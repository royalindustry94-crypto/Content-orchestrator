"""Defense-in-depth service scoping for Content Desk operations.

These tests deliberately call `app.services.content_desk` through the
owner connection, bypassing both FastAPI authorization guards and RLS.
They prove the service layer's explicit `workspace_id` filters remain
effective independently of migration 0052 and the request-scoped
`app_runtime` route path.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, rls_scoped_session
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.services import content_desk
from app.services.spend import ensure_default_spend_cap


async def _create_user_workspace_and_gate(session, topic: str):
    user_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    await session.execute(
        text(
            "INSERT INTO profiles (id, email) VALUES (:id, :email) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    ws = Workspace(id=uuid.uuid4(), name=f"scope-{user_id}", created_by=user_id)
    session.add(ws)
    await session.flush()
    session.add(
        WorkspaceMembership(workspace_id=ws.id, user_id=user_id, role=WorkspaceRole.ADMIN)
    )
    await ensure_default_spend_cap(session, workspace_id=ws.id, actor_id=user_id)
    result = await content_desk.create_content_job(
        session,
        workspace_id=ws.id,
        actor_id=user_id,
        topic=topic,
        script_body="body",
    )
    await session.commit()
    return ws.id, result


@pytest.mark.asyncio
async def test_content_desk_service_never_returns_another_workspaces_gate():
    async with AsyncSessionLocal() as session:
        workspace_a, result_a = await _create_user_workspace_and_gate(
            session, "Workspace A topic"
        )
    async with AsyncSessionLocal() as session:
        workspace_b, _result_b = await _create_user_workspace_and_gate(
            session, "Workspace B topic"
        )

    async with AsyncSessionLocal() as session:
        # No FastAPI guard in the loop — as if the membership check were
        # missing or buggy. Only the service's own workspace_id filter can
        # prevent workspace B from reading workspace A's gate.
        row = await content_desk.get_review_gate(
            session, workspace_id=workspace_b, gate_id=result_a.review_gate_id
        )
        assert row is None, (
            "content_desk.get_review_gate leaked a review gate across "
            "workspaces in the deliberately owner-scoped service test"
        )

        rows = await content_desk.list_review_gates(session, workspace_id=workspace_b)
        assert all(r["id"] != result_a.review_gate_id for r in rows), (
            "content_desk.list_review_gates leaked another workspace's gate"
        )


@pytest.mark.asyncio
async def test_content_desk_decide_review_gate_rejects_mismatched_workspace():
    async with AsyncSessionLocal() as session:
        workspace_a, result_a = await _create_user_workspace_and_gate(
            session, "Decide isolation A"
        )
    async with AsyncSessionLocal() as session:
        workspace_b, _result_b = await _create_user_workspace_and_gate(
            session, "Decide isolation B"
        )

    async with AsyncSessionLocal() as session:
        with pytest.raises(content_desk.ReviewGateNotFoundError):
            await content_desk.decide_review_gate(
                session,
                workspace_id=workspace_b,
                gate_id=result_a.review_gate_id,
                reviewer_id=uuid.uuid4(),
                approved=True,
            )
        await session.rollback()

    # The gate in workspace A must be unaffected by the rejected cross-tenant
    # attempt (still AWAITING, not accidentally approved).
    async with AsyncSessionLocal() as session:
        row = await content_desk.get_review_gate(
            session, workspace_id=workspace_a, gate_id=result_a.review_gate_id
        )
        assert row is not None
        assert row["status"] == "awaiting"


@pytest.mark.asyncio
async def test_reviewer_runtime_session_can_sequence_review_decision_event():
    """A reviewer must see prior aggregate outbox rows to allocate sequence N+1.

    The creator emits pipeline events before review. If reviewer SELECT on
    `outbox_events` is missing, RLS hides those rows from `_next_sequence()`,
    which reuses sequence 1 and violates the aggregate-sequence unique index.
    """
    async with AsyncSessionLocal() as session:
        workspace_id, result = await _create_user_workspace_and_gate(
            session, "Reviewer outbox sequence"
        )
        reviewer_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(reviewer_id), "email": f"{reviewer_id}@example.com"},
        )
        await session.execute(
            text(
                "INSERT INTO profiles (id, email) VALUES (:id, :email) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(reviewer_id), "email": f"{reviewer_id}@example.com"},
        )
        session.add(
            WorkspaceMembership(
                workspace_id=workspace_id,
                user_id=reviewer_id,
                role=WorkspaceRole.REVIEWER,
            )
        )
        await session.commit()

    async with rls_scoped_session(str(reviewer_id)) as session:
        detail = await content_desk.decide_review_gate(
            session,
            workspace_id=workspace_id,
            gate_id=result.review_gate_id,
            reviewer_id=reviewer_id,
            approved=True,
        )
        await session.commit()

    assert detail["status"] != "awaiting"
