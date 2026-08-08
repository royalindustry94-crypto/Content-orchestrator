"""Proves Row Level Security itself works — not just the FastAPI guard.

Bypasses app.core.authorization entirely and queries through
rls_scoped_session directly, as if an app-layer guard were missing or
buggy. If this test passes while a guard is broken, RLS is still the
backstop the design doc promises.
"""

import uuid

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal, rls_scoped_session
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole


async def _create_user_and_workspace(name: str) -> tuple[str, uuid.UUID]:
    user_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": user_id, "email": f"{user_id}@example.com"},
        )
        await session.commit()

    async with rls_scoped_session(user_id) as session:
        workspace = Workspace(name=name, created_by=uuid.UUID(user_id))
        session.add(workspace)
        await session.flush()
        session.add(
            WorkspaceMembership(
                workspace_id=workspace.id, user_id=uuid.UUID(user_id), role=WorkspaceRole.ADMIN
            )
        )
        await session.commit()
        return user_id, workspace.id


@pytest.mark.asyncio
async def test_rls_blocks_cross_workspace_read_even_without_app_guard():
    user_a, workspace_a = await _create_user_and_workspace("Workspace A")
    user_b, workspace_b = await _create_user_and_workspace("Workspace B")

    # User B, scoped via RLS only (no app.core.authorization guard in the
    # loop at all), tries to read workspace A directly.
    async with rls_scoped_session(user_b) as session:
        result = await session.execute(select(Workspace).where(Workspace.id == workspace_a))
        assert result.scalar_one_or_none() is None, (
            "RLS failed to block user B from reading workspace A's row"
        )

        # Sanity check: user B CAN see their own workspace through the
        # same session, so the empty result above is RLS filtering, not a
        # broken query.
        own = await session.execute(select(Workspace).where(Workspace.id == workspace_b))
        assert own.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_rls_blocks_cross_workspace_membership_read():
    user_a, workspace_a = await _create_user_and_workspace("Membership A")
    user_b, _workspace_b = await _create_user_and_workspace("Membership B")

    async with rls_scoped_session(user_b) as session:
        result = await session.execute(
            select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_a)
        )
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_rls_blocks_cross_workspace_leads_and_worker_logs():
    user_a, workspace_a = await _create_user_and_workspace("Operations tenant A")
    user_b, _workspace_b = await _create_user_and_workspace("Operations tenant B")
    worker_id = uuid.uuid4()

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO leads (workspace_id, name, email)
                VALUES (:workspace_id, 'Private lead', 'private@example.com')
                """
            ),
            {"workspace_id": str(workspace_a)},
        )
        await session.execute(
            text(
                """
                INSERT INTO worker_registry (
                    id, workspace_id, name, supported_stages, status,
                    max_concurrency, current_load, health_score, instance_key
                ) VALUES (
                    :id, :workspace_id, 'private-worker', ARRAY['scripting'],
                    'online'::worker_status, 1, 0, 100, :instance_key
                )
                """
            ),
            {
                "id": str(worker_id),
                "workspace_id": str(workspace_a),
                "instance_key": f"private-{worker_id}",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO worker_logs (
                    workspace_id, worker_id, severity, message
                ) VALUES (
                    :workspace_id, :worker_id, 'info', 'tenant-private log'
                )
                """
            ),
            {"workspace_id": str(workspace_a), "worker_id": str(worker_id)},
        )
        await session.commit()

    # The owning admin can see both records through the runtime role.
    async with rls_scoped_session(user_a) as session:
        assert await session.scalar(
            text("SELECT count(*) FROM leads WHERE workspace_id = :workspace_id"),
            {"workspace_id": str(workspace_a)},
        ) == 1
        assert await session.scalar(
            text("SELECT count(*) FROM worker_logs WHERE workspace_id = :workspace_id"),
            {"workspace_id": str(workspace_a)},
        ) == 1

    # A different tenant sees no rows even when querying directly without
    # FastAPI authorization guards.
    async with rls_scoped_session(user_b) as session:
        assert await session.scalar(
            text("SELECT count(*) FROM leads WHERE workspace_id = :workspace_id"),
            {"workspace_id": str(workspace_a)},
        ) == 0
        assert await session.scalar(
            text("SELECT count(*) FROM worker_logs WHERE workspace_id = :workspace_id"),
            {"workspace_id": str(workspace_a)},
        ) == 0
