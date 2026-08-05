"""Schema tests for the four Milestone 3 amendments (idempotency, lineage,
asset storage metadata, provider metadata). Run against real Postgres in CI
after `alembic upgrade head`.
"""

import os
import uuid

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


async def _make_workspace_and_item(s):
    ws, user, item = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    await s.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
                    {"id": user, "e": f"{user}@x.com"})
    await s.execute(
        text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"),
        {"id": ws, "u": user})
    await s.execute(
        text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
        {"id": item, "ws": ws})
    return ws, user, item


@pytest.mark.asyncio
async def test_pipeline_run_idempotency_key_unique_per_workspace():
    async with AsyncSessionLocal() as s:
        ws, _u, item = await _make_workspace_and_item(s)
        await s.commit()
        await s.execute(
            text("INSERT INTO pipeline_runs (workspace_id, content_item_id, idempotency_key) "
                 "VALUES (:ws, :item, 'key-1')"),
            {"ws": ws, "item": item},
        )
        await s.commit()
        with pytest.raises(Exception) as exc:
            await s.execute(
                text("INSERT INTO pipeline_runs (workspace_id, content_item_id, idempotency_key) "
                     "VALUES (:ws, :item, 'key-1')"),
                {"ws": ws, "item": item},
            )
            await s.commit()
        assert "unique" in str(exc.value).lower() or "duplicate" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_content_lineage_rejects_self_reference():
    async with AsyncSessionLocal() as s:
        ws, _u, item = await _make_workspace_and_item(s)
        await s.commit()
        with pytest.raises(Exception) as exc:
            await s.execute(
                text(
                    "INSERT INTO content_lineage "
                    "(workspace_id, parent_content_item_id, "
                    "child_content_item_id, relationship_type) "
                    "VALUES (:ws, :item, :item, 'remixed')"
                ),
                {"ws": ws, "item": item},
            )
            await s.commit()
        assert "ck_content_lineage_no_self" in str(exc.value) or "check" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_content_lineage_is_immutable():
    async with AsyncSessionLocal() as s:
        ws, _u, parent = await _make_workspace_and_item(s)
        child = str(uuid.uuid4())
        await s.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't2')"),
            {"id": child, "ws": ws})
        edge = str(uuid.uuid4())
        await s.execute(
            text("INSERT INTO content_lineage (id, workspace_id, parent_content_item_id, "
                 "child_content_item_id, relationship_type) VALUES (:id, :ws, :p, :c, 'clipped')"),
            {"id": edge, "ws": ws, "p": parent, "c": child},
        )
        await s.commit()
        with pytest.raises(Exception) as exc:
            await s.execute(
                text("UPDATE content_lineage SET notes = 'x' WHERE id = :id"), {"id": edge})
            await s.commit()
        assert "immutable" in str(exc.value).lower()


@pytest.mark.asyncio
async def test_asset_storage_and_provider_metadata_columns_exist():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text("SELECT column_name FROM information_schema.columns "
                 "WHERE table_name = 'assets'")
        )
        cols = {r[0] for r in rows}
    for expected in [
        "storage_provider", "storage_bucket", "storage_object_key",
        "checksum", "checksum_algorithm", "mime_type", "size_bytes",
        "provider_metadata",
    ]:
        assert expected in cols, f"assets missing column {expected}"


@pytest.mark.asyncio
async def test_provider_metadata_on_immutable_tables():
    async with AsyncSessionLocal() as s:
        for table in ["pipeline_stage_runs", "provider_usage", "spend_logs"]:
            rows = await s.execute(
                text("SELECT 1 FROM information_schema.columns "
                     "WHERE table_name = :t AND column_name = 'provider_metadata'"),
                {"t": table},
            )
            assert rows.first() is not None, f"{table} missing provider_metadata"
