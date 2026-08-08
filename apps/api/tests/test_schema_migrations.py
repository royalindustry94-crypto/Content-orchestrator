"""Schema-level tests for the Milestone 3 content domain.

These run against the real Postgres in CI after `alembic upgrade head`,
so they verify the migrations actually applied and the DB-level guarantees
(RLS enabled, immutability triggers, version defaults) are really in place
— not just that the ORM models parse.
"""

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test"
)
os.environ.setdefault(
    "APP_DATABASE_URL",
    "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test",
)
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret-0123456789abcdef")

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

DOMAIN_TABLES = [
    "content_pillars", "spend_caps", "provider_credentials",
    "content_items", "content_versions", "pipeline_runs", "pipeline_stage_runs",
    "assets", "publish_jobs", "review_decisions", "analytics_snapshots",
    "spend_logs", "spend_reservations", "provider_usage",
    "webhook_events", "dead_letter_jobs",
    "leads", "worker_logs",
]

IMMUTABLE_TABLES = [
    "content_versions", "pipeline_stage_runs", "review_decisions",
    "analytics_snapshots", "spend_logs", "provider_usage",
    "worker_logs",
]


@pytest.mark.asyncio
async def test_all_domain_tables_exist():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        )
        present = {r[0] for r in rows}
    missing = [t for t in DOMAIN_TABLES if t not in present]
    assert not missing, f"missing tables: {missing}"


@pytest.mark.asyncio
async def test_rls_forced_on_every_domain_table():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                "SELECT relname FROM pg_class "
                "WHERE relrowsecurity AND relforcerowsecurity AND relkind = 'r'"
            )
        )
        forced = {r[0] for r in rows}
    missing = [t for t in DOMAIN_TABLES if t not in forced]
    assert not missing, f"RLS not FORCED on: {missing}"


@pytest.mark.asyncio
async def test_immutable_tables_reject_update():
    # Insert a content item + version via owner session, then try to UPDATE
    # the (immutable) version row — the prevent_update trigger must raise.
    import uuid

    ws = str(uuid.uuid4())
    user = str(uuid.uuid4())
    item = str(uuid.uuid4())
    ver = str(uuid.uuid4())
    async with AsyncSessionLocal() as s:
        await s.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
                        {"id": user, "e": f"{user}@x.com"})
        await s.execute(text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"),
                        {"id": ws, "u": user})
        await s.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": item, "ws": ws},
        )
        await s.execute(
            text("INSERT INTO content_versions (id, workspace_id, content_item_id, script_body) "
                 "VALUES (:id, :ws, :item, 'body')"),
            {"id": ver, "ws": ws, "item": item},
        )
        await s.commit()

        with pytest.raises(Exception) as exc:
            await s.execute(
                text("UPDATE content_versions SET script_body = 'edited' WHERE id = :id"),
                {"id": ver},
            )
            await s.commit()
        assert "immutable" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_worker_logs_reject_update_and_delete():
    import uuid

    user_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())
    worker_id = str(uuid.uuid4())
    log_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": user_id, "email": f"{user_id}@example.com"},
        )
        await session.execute(
            text(
                "INSERT INTO workspaces (id, name, created_by) "
                "VALUES (:id, 'worker-log-audit', :user_id)"
            ),
            {"id": workspace_id, "user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO worker_registry (
                    id, workspace_id, name, supported_stages, status,
                    max_concurrency, current_load, health_score, instance_key
                ) VALUES (
                    :id, :workspace_id, 'audit-worker', ARRAY['scripting'],
                    'online'::worker_status, 1, 0, 100, :instance_key
                )
                """
            ),
            {
                "id": worker_id,
                "workspace_id": workspace_id,
                "instance_key": f"audit-{worker_id}",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO worker_logs (
                    id, workspace_id, worker_id, severity, message
                ) VALUES (:id, :workspace_id, :worker_id, 'info', 'immutable')
                """
            ),
            {
                "id": log_id,
                "workspace_id": workspace_id,
                "worker_id": worker_id,
            },
        )
        await session.commit()

        with pytest.raises(Exception) as update_exc:
            await session.execute(
                text("UPDATE worker_logs SET message = 'rewritten' WHERE id = :id"),
                {"id": log_id},
            )
        assert "immutable" in str(update_exc.value).lower()
        await session.rollback()

        with pytest.raises(Exception) as delete_exc:
            await session.execute(
                text("DELETE FROM worker_logs WHERE id = :id"),
                {"id": log_id},
            )
        assert "immutable" in str(delete_exc.value).lower()
        await session.rollback()


@pytest.mark.asyncio
async def test_version_trigger_increments_on_mutable_table():
    import uuid

    ws = str(uuid.uuid4())
    user = str(uuid.uuid4())
    item = str(uuid.uuid4())
    async with AsyncSessionLocal() as s:
        await s.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
                        {"id": user, "e": f"{user}@x.com"})
        await s.execute(text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"),
                        {"id": ws, "u": user})
        await s.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": item, "ws": ws},
        )
        await s.commit()
        await s.execute(text("UPDATE content_items SET topic = 't2' WHERE id = :id"), {"id": item})
        await s.commit()
        row = await s.execute(
            text("SELECT version FROM content_items WHERE id = :id"), {"id": item}
        )
        assert row.scalar_one() == 2
