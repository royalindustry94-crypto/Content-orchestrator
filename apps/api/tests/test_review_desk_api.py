"""Private Beta Review Desk HTTP API — content jobs + review decisions."""

from __future__ import annotations

import asyncio
import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.content import ContentItem
from app.models.pipeline import PipelineRun
from app.models.review_gate import ReviewGate
from app.models.workspace_membership import WorkspaceRole


async def _create_workspace(client, headers: dict) -> str:
    response = await client.post(
        "/workspaces",
        headers=headers,
        json={"name": f"desk-{uuid.uuid4().hex[:8]}"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _add_member(
    client, *, workspace_id: str, admin_headers: dict, member_user_id: str, role: str
) -> None:
    response = await client.post(
        f"/workspaces/{workspace_id}/memberships",
        headers=admin_headers,
        json={"user_id": member_user_id, "role": role},
    )
    assert response.status_code == 201, response.text


async def _current_version_id(client, *, workspace_id: str, gate_id: str, headers: dict) -> str:
    response = await client.get(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
    )
    assert response.status_code == 200, response.text
    version_id = response.json()["content_version_id"]
    assert version_id is not None
    return version_id


@pytest.mark.asyncio
async def test_content_job_lands_in_review_gate(client, new_user):
    user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)

    response = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={
            "topic": "Weekly product update",
            "script_hook": "Ship faster with review.",
            "script_body": "Draft body for human review.",
            "script_cta": "Subscribe",
            "idempotency_key": "job-1",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["gate_status"] == "awaiting"
    assert body["current_stage"] == "review"
    assert body["topic"] == "Weekly product update"

    queue = await client.get(
        f"/workspaces/{workspace_id}/review-gates",
        headers=headers,
    )
    assert queue.status_code == 200
    gates = queue.json()
    assert len(gates) == 1
    assert gates[0]["id"] == body["review_gate_id"]
    assert gates[0]["script_body"] == "Draft body for human review."
    assert gates[0]["status"] == "awaiting"

    async with AsyncSessionLocal() as session:
        gate = await session.get(ReviewGate, uuid.UUID(body["review_gate_id"]))
        item = await session.get(ContentItem, uuid.UUID(body["content_item_id"]))
        assert gate is not None and item is not None
        assert gate.content_version_id == item.current_version_id
        assert gate.content_version_id is not None


@pytest.mark.asyncio
async def test_approve_advances_to_published(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={
            "topic": "Approve me",
            "script_body": "Body",
        },
    )
    assert created.status_code == 201, created.text
    gate_id = created.json()["review_gate_id"]
    run_id = created.json()["pipeline_run_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={
            "approved": True,
            "notes": "Looks good",
            "expected_content_version_id": version_id,
        },
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "approved"
    assert decided.json()["run_status"] in {"succeeded", "running"}

    async with AsyncSessionLocal() as session:
        run = await session.get(PipelineRun, uuid.UUID(run_id))
        assert run is not None
        status = run.status.value if hasattr(run.status, "value") else run.status
        stage = (
            run.current_stage.value if hasattr(run.current_stage, "value") else run.current_stage
        )
        assert status == "succeeded"
        assert stage == "published"


@pytest.mark.asyncio
async def test_edit_review_gate_content_creates_new_version_and_stays_publishable(client, new_user):
    """Editing before approval must move both `item.current_version_id`
    and the gate's frozen `content_version_id` snapshot together, or a
    legitimately edited-then-approved item would be permanently blocked
    from publication by its own review gate (see publication_policy's
    `review_gate_content_version_mismatch` check)."""
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={
            "topic": "Edit me",
            "script_hook": "Original hook",
            "script_body": "Original body",
            "script_cta": "Original cta",
        },
    )
    assert created.status_code == 201, created.text
    gate_id = created.json()["review_gate_id"]
    content_item_id = created.json()["content_item_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    edited = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_body": "Edited body", "expected_content_version_id": version_id},
    )
    assert edited.status_code == 200, edited.text
    body = edited.json()
    assert body["script_body"] == "Edited body"
    # Omitted fields keep their prior value rather than being cleared.
    assert body["script_hook"] == "Original hook"
    assert body["script_cta"] == "Original cta"
    assert body["status"] == "awaiting"

    async with AsyncSessionLocal() as session:
        gate = await session.get(ReviewGate, uuid.UUID(gate_id))
        item = await session.get(ContentItem, uuid.UUID(content_item_id))
        assert gate is not None and item is not None
        assert gate.content_version_id == item.current_version_id
        assert gate.content_version_id is not None

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "expected_content_version_id": body["content_version_id"]},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["script_body"] == "Edited body"


@pytest.mark.asyncio
async def test_edit_review_gate_content_rejects_decided_gate(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Already decided", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "expected_content_version_id": version_id},
    )
    assert decided.status_code == 200, decided.text

    blocked = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_body": "Too late", "expected_content_version_id": version_id},
    )
    assert blocked.status_code == 409


@pytest.mark.asyncio
async def test_edit_review_gate_content_requires_at_least_one_field(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Empty edit", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    empty = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"expected_content_version_id": version_id},
    )
    assert empty.status_code == 422


@pytest.mark.asyncio
async def test_reviewer_only_cannot_edit_review_gate_content(client, new_user):
    admin_id, _admin_token, admin_headers = new_user
    workspace_id = await _create_workspace(client, admin_headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=admin_headers,
        json={"topic": "Reviewer cannot edit", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=admin_headers
    )

    reviewer_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": reviewer_id, "email": f"{reviewer_id}@example.com"},
        )
        await session.commit()
    from tests.conftest import make_token

    reviewer_headers = {"Authorization": f"Bearer {make_token(user_id=reviewer_id)}"}
    await _add_member(
        client,
        workspace_id=workspace_id,
        admin_headers=admin_headers,
        member_user_id=reviewer_id,
        role=WorkspaceRole.REVIEWER.value,
    )

    forbidden = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=reviewer_headers,
        json={"script_body": "Reviewer edit", "expected_content_version_id": version_id},
    )
    assert forbidden.status_code == 403
    assert admin_id  # silence unused in some linters


@pytest.mark.asyncio
async def test_editor_can_edit_review_gate_content_under_rls(client, new_user):
    """Regression for an independent-audit P1: the FastAPI guard on the
    PATCH route admits admin/editor, but `edit_review_gate_content`'s
    `SELECT ... FOR UPDATE` on `review_gates` also has to satisfy the
    table's RLS UPDATE policy (migration 0056) or PostgreSQL silently
    zero-rows the locking read and the route 404s despite passing auth."""
    admin_id, _admin_token, admin_headers = new_user
    workspace_id = await _create_workspace(client, admin_headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=admin_headers,
        json={"topic": "Editor can edit", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=admin_headers
    )

    editor_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": editor_id, "email": f"{editor_id}@example.com"},
        )
        await session.commit()
    from tests.conftest import make_token

    editor_headers = {"Authorization": f"Bearer {make_token(user_id=editor_id)}"}
    await _add_member(
        client,
        workspace_id=workspace_id,
        admin_headers=admin_headers,
        member_user_id=editor_id,
        role=WorkspaceRole.EDITOR.value,
    )

    edited = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=editor_headers,
        json={"script_body": "Editor edit", "expected_content_version_id": version_id},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["script_body"] == "Editor edit"
    assert admin_id  # silence unused in some linters


@pytest.mark.asyncio
async def test_decision_rejects_stale_expected_content_version(client, new_user):
    """Regression for an independent-audit P1: a reviewer's client could
    have gate V1 open in its drawer; if the content is edited to V2
    before the reviewer clicks Approve, the decision must not silently
    bind to V2 — the reviewer never saw it."""
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Version race", "script_body": "V1 body"},
    )
    gate_id = created.json()["review_gate_id"]

    loaded = await client.get(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
    )
    v1_version_id = loaded.json()["content_version_id"]
    assert v1_version_id is not None

    edited = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_body": "V2 body", "expected_content_version_id": v1_version_id},
    )
    assert edited.status_code == 200, edited.text
    v2_version_id = edited.json()["content_version_id"]
    assert v2_version_id != v1_version_id

    stale_decision = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "expected_content_version_id": v1_version_id},
    )
    assert stale_decision.status_code == 409, stale_decision.text

    async with AsyncSessionLocal() as session:
        gate = await session.get(ReviewGate, uuid.UUID(gate_id))
        assert gate is not None
        assert gate.status.value == "awaiting"

    fresh_decision = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "expected_content_version_id": v2_version_id},
    )
    assert fresh_decision.status_code == 200, fresh_decision.text
    assert fresh_decision.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_decision_requires_expected_version(client, new_user):
    """expected_content_version_id is required, not optional — an
    independent-audit finding on the first version of this fix: an
    optional check a caller can simply omit protects nothing against a
    client (present or future, UI or direct API) that doesn't opt in."""
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "No version pin", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True},
    )
    assert decided.status_code == 422, decided.text


@pytest.mark.asyncio
async def test_edit_rejects_stale_expected_content_version(client, new_user):
    """Regression for an independent-audit P2 (round 3): a second editor
    saving a draft loaded before someone else's edit landed must not
    silently clobber it — a save submits all three script fields, so it
    would overwrite even fields only the first editor touched."""
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={
            "topic": "Concurrent editors",
            "script_hook": "Hook V1",
            "script_body": "Body V1",
            "script_cta": "CTA V1",
        },
    )
    gate_id = created.json()["review_gate_id"]
    v1_version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    # Editor A saves first, moving the gate to V2.
    edited_a = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_hook": "Hook V2 by A", "expected_content_version_id": v1_version_id},
    )
    assert edited_a.status_code == 200, edited_a.text

    # Editor B's drawer was still showing V1 when they save — must conflict,
    # not silently overwrite A's script_hook change with the stale V1 value.
    stale_edit_b = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_body": "Body V2 by B (stale)", "expected_content_version_id": v1_version_id},
    )
    assert stale_edit_b.status_code == 409, stale_edit_b.text

    # B refreshes and retries against the real current version — succeeds.
    v2_version_id = edited_a.json()["content_version_id"]
    fresh_edit_b = await client.patch(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}",
        headers=headers,
        json={"script_body": "Body V3 by B", "expected_content_version_id": v2_version_id},
    )
    assert fresh_edit_b.status_code == 200, fresh_edit_b.text
    body = fresh_edit_b.json()
    assert body["script_body"] == "Body V3 by B"
    # A's hook change survives — B's save only touched script_body.
    assert body["script_hook"] == "Hook V2 by A"


@pytest.mark.asyncio
async def test_versionless_review_gate_can_be_rejected_but_not_approved(client, new_user):
    """Regression for an independent-audit P2 (round 3): historical review
    gates predating migration 0040 have `content_version_id = NULL` (see
    `ReviewGate.content_version_id`'s docstring) and must still be
    rejectable even though they can never be approved (publication's
    anti-tamper check treats a null snapshot as fail-closed)."""
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Versionless historical gate", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]

    async with AsyncSessionLocal() as session:
        gate = await session.get(ReviewGate, uuid.UUID(gate_id))
        assert gate is not None
        gate.content_version_id = None
        await session.commit()

    blocked_approval = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "expected_content_version_id": str(uuid.uuid4())},
    )
    assert blocked_approval.status_code == 409, blocked_approval.text

    rejected = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": False},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_reject_fails_run_without_reject_transition(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Reject me", "script_body": "Body"},
    )
    gate_id = created.json()["review_gate_id"]
    run_id = created.json()["pipeline_run_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": False, "notes": "Off brand", "expected_content_version_id": version_id},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "rejected"

    async with AsyncSessionLocal() as session:
        run = await session.get(PipelineRun, uuid.UUID(run_id))
        status = run.status.value if hasattr(run.status, "value") else run.status
        assert status == "failed"


@pytest.mark.asyncio
async def test_editor_cannot_decide_review_gate(client, new_user):
    admin_id, _admin_token, admin_headers = new_user
    workspace_id = await _create_workspace(client, admin_headers)

    # Second user as editor
    editor_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": editor_id, "email": f"{editor_id}@example.com"},
        )
        await session.commit()
    from tests.conftest import make_token

    editor_headers = {"Authorization": f"Bearer {make_token(user_id=editor_id)}"}
    await _add_member(
        client,
        workspace_id=workspace_id,
        admin_headers=admin_headers,
        member_user_id=editor_id,
        role=WorkspaceRole.EDITOR.value,
    )

    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=editor_headers,
        json={"topic": "Editor draft", "script_body": "Body"},
    )
    assert created.status_code == 201, created.text
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=editor_headers
    )

    forbidden = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=editor_headers,
        json={"approved": True, "expected_content_version_id": version_id},
    )
    assert forbidden.status_code == 403
    assert admin_id  # silence unused in some linters


@pytest.mark.asyncio
async def test_cross_workspace_review_gate_is_hidden(client, new_user):
    _user_a, _token_a, headers_a = new_user
    workspace_a = await _create_workspace(client, headers_a)
    created = await client.post(
        f"/workspaces/{workspace_a}/content-jobs",
        headers=headers_a,
        json={"topic": "A only", "script_body": "secret"},
    )
    gate_id = created.json()["review_gate_id"]

    user_b = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": user_b, "email": f"{user_b}@example.com"},
        )
        await session.commit()
    from tests.conftest import make_token

    headers_b = {"Authorization": f"Bearer {make_token(user_id=user_b)}"}
    workspace_b = await _create_workspace(client, headers_b)

    missing = await client.get(
        f"/workspaces/{workspace_b}/review-gates/{gate_id}",
        headers=headers_b,
    )
    assert missing.status_code == 404

    forbidden_list = await client.get(
        f"/workspaces/{workspace_a}/review-gates",
        headers=headers_b,
    )
    assert forbidden_list.status_code == 403


@pytest.mark.asyncio
async def test_idempotent_content_job_returns_same_gate(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    payload = {
        "topic": "Idempotent",
        "script_body": "Body",
        "idempotency_key": "same-key",
    }
    first = await client.post(
        f"/workspaces/{workspace_id}/content-jobs", headers=headers, json=payload
    )
    second = await client.post(
        f"/workspaces/{workspace_id}/content-jobs", headers=headers, json=payload
    )
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["review_gate_id"] == second.json()["review_gate_id"]
    assert first.json()["pipeline_run_id"] == second.json()["pipeline_run_id"]

    async with AsyncSessionLocal() as session:
        gates = (
            (
                await session.execute(
                    select(ReviewGate).where(ReviewGate.workspace_id == uuid.UUID(workspace_id))
                )
            )
            .scalars()
            .all()
        )
        assert len(gates) == 1


@pytest.mark.asyncio
async def test_concurrent_review_decisions_are_serialized(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _create_workspace(client, headers)
    created = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Concurrent decision", "script_body": "Body"},
    )
    assert created.status_code == 201, created.text
    gate_id = created.json()["review_gate_id"]
    version_id = await _current_version_id(
        client, workspace_id=workspace_id, gate_id=gate_id, headers=headers
    )

    approve, reject = await asyncio.gather(
        client.post(
            f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
            headers=headers,
            json={
                "approved": True,
                "notes": "approve race",
                "expected_content_version_id": version_id,
            },
        ),
        client.post(
            f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
            headers=headers,
            json={
                "approved": False,
                "notes": "reject race",
                "expected_content_version_id": version_id,
            },
        ),
    )

    assert sorted((approve.status_code, reject.status_code)) == [200, 409]
    decided = approve if approve.status_code == 200 else reject
    assert decided.json()["status"] in {"approved", "rejected"}
    assert decided.json()["decided_at"] is not None
