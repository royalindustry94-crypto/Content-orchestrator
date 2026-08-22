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

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": True, "notes": "Looks good"},
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

    decided = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=headers,
        json={"approved": False, "notes": "Off brand"},
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

    forbidden = await client.post(
        f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
        headers=editor_headers,
        json={"approved": True},
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

    approve, reject = await asyncio.gather(
        client.post(
            f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
            headers=headers,
            json={"approved": True, "notes": "approve race"},
        ),
        client.post(
            f"/workspaces/{workspace_id}/review-gates/{gate_id}/decision",
            headers=headers,
            json={"approved": False, "notes": "reject race"},
        ),
    )

    assert sorted((approve.status_code, reject.status_code)) == [200, 409]
    decided = approve if approve.status_code == 200 else reject
    assert decided.json()["status"] in {"approved", "rejected"}
    assert decided.json()["decided_at"] is not None
