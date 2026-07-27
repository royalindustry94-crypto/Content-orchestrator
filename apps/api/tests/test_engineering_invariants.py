"""Engineering foundation invariants — executable, CI-enforced.

Complements existing schema/RLS tests with catalog-level checks required by
the Cursor foundation refactor (CEO directive). Runs against real Postgres
after `alembic upgrade head`.
"""

from __future__ import annotations

import os

os.environ.setdefault(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test"
)
os.environ.setdefault(
    "APP_DATABASE_URL",
    "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test",
)
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

# Tenant-owned user-data tables expected to carry workspace_id + FORCE RLS.
# Infrastructure tables (worker_registry, etc.) are intentionally excluded.
TENANT_TABLES = [
    "content_pillars",
    "spend_caps",
    "provider_credentials",
    "content_items",
    "content_versions",
    "pipeline_runs",
    "pipeline_stage_runs",
    "assets",
    "publish_jobs",
    "review_decisions",
    "analytics_snapshots",
    "spend_logs",
    "spend_reservations",
    "provider_usage",
    "webhook_events",
    "dead_letter_jobs",
    "workspace_memberships",
]

IMMUTABLE_TABLES = [
    "content_versions",
    "pipeline_stage_runs",
    "review_decisions",
    "analytics_snapshots",
    "spend_logs",
    "provider_usage",
]

SOFT_DELETE_TABLES = [
    "content_items",
    "assets",
    "publish_jobs",
]

OPTIMISTIC_VERSION_TABLES = [
    "content_items",
    "assets",
    "publish_jobs",
    "pipeline_runs",
]


@pytest.mark.asyncio
async def test_tenant_tables_have_workspace_id():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT table_name FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'workspace_id'
                """
            )
        )
        with_ws = {r[0] for r in rows}
    missing = [t for t in TENANT_TABLES if t not in with_ws]
    assert not missing, f"tenant tables missing workspace_id: {missing}"


@pytest.mark.asyncio
async def test_enable_and_force_rls_on_tenant_tables():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relkind = 'r'
                """
            )
        )
        flags = {r[0]: (r[1], r[2]) for r in rows}
    missing_enable = [t for t in TENANT_TABLES if t not in flags or not flags[t][0]]
    missing_force = [t for t in TENANT_TABLES if t not in flags or not flags[t][1]]
    assert not missing_enable, f"ENABLE RLS missing: {missing_enable}"
    assert not missing_force, f"FORCE RLS missing: {missing_force}"


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_workspace_id_foreign_keys_are_indexed():
    """workspace_id FKs must be leading-indexed (tenant hot path)."""
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT
                  con.conrelid::regclass::text AS table_name,
                  con.conname,
                  array_agg(att.attname ORDER BY u.ord) AS fk_cols
                FROM pg_constraint con
                JOIN pg_namespace n ON n.oid = con.connamespace AND n.nspname = 'public'
                CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
                JOIN pg_attribute att
                  ON att.attrelid = con.conrelid AND att.attnum = u.attnum
                WHERE con.contype = 'f'
                GROUP BY con.conrelid, con.conname
                """
            )
        )
        fks = list(rows)

        idx_rows = await s.execute(
            text(
                """
                SELECT
                  t.relname AS table_name,
                  array_agg(a.attname ORDER BY x.n) AS idx_cols
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace AND n.nspname = 'public'
                JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS x(attnum, n) ON true
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
                WHERE i.indisvalid AND a.attnum > 0
                GROUP BY t.relname, i.indexrelid
                """
            )
        )
        indexes_by_table: dict[str, list[list[str]]] = {}
        for table_name, idx_cols in idx_rows:
            indexes_by_table.setdefault(table_name, []).append(list(idx_cols))

    missing = []
    known_workspace_id_gaps = {
        # Historical: composite/other indexes exist but not workspace_id-leading.
        # Tracked for a follow-up Alembic index migration.
        "workflow_stages.workflow_stages_workspace_id_fkey(workspace_id)",
        "workflow_transitions.workflow_transitions_workspace_id_fkey(workspace_id)",
        "worker_registry.worker_registry_workspace_id_fkey(workspace_id)",
        "worker_credentials.worker_credentials_workspace_id_fkey(workspace_id)",
    }
    for table_name, conname, fk_cols in fks:
        fk_list = list(fk_cols)
        if fk_list != ["workspace_id"]:
            continue
        key = f"{table_name}.{conname}({','.join(fk_list)})"
        if key in known_workspace_id_gaps:
            continue
        table_indexes = indexes_by_table.get(table_name, [])
        covered = any(idx[:1] == ["workspace_id"] for idx in table_indexes)
        if not covered:
            missing.append(key)
    assert not missing, f"workspace_id FK without supporting index: {missing}"


@pytest.mark.asyncio
async def test_foreign_key_index_gaps_are_allowlisted():
    """Full FK index audit — known historical gaps allowlisted; no new gaps.

    Adding indexes for every actor FK (created_by/updated_by) is tracked as
    follow-up schema work; this test prevents silent regression.
    """
    known_gaps = {
        "workspaces.workspaces_created_by_fkey(created_by)",
        "workspace_memberships.workspace_memberships_user_id_fkey(user_id)",
        "content_pillars.content_pillars_created_by_fkey(created_by)",
        "content_pillars.content_pillars_updated_by_fkey(updated_by)",
        "spend_caps.spend_caps_created_by_fkey(created_by)",
        "spend_caps.spend_caps_updated_by_fkey(updated_by)",
        "provider_credentials.provider_credentials_created_by_fkey(created_by)",
        "provider_credentials.provider_credentials_updated_by_fkey(updated_by)",
        "content_items.content_items_created_by_fkey(created_by)",
        "content_items.content_items_pillar_id_fkey(pillar_id)",
        "content_items.content_items_updated_by_fkey(updated_by)",
        "content_items.fk_content_items_current_run(current_pipeline_run_id)",
        "content_items.fk_content_items_current_version(current_version_id)",
        "content_versions.content_versions_created_by_fkey(created_by)",
        "pipeline_runs.fk_pipeline_runs_definition(definition_id)",
        "pipeline_stage_runs.pipeline_stage_runs_content_item_id_fkey(content_item_id)",
        "assets.assets_content_version_id_fkey(content_version_id)",
        "assets.assets_created_by_fkey(created_by)",
        "assets.assets_updated_by_fkey(updated_by)",
        "publish_jobs.publish_jobs_created_by_fkey(created_by)",
        "publish_jobs.publish_jobs_updated_by_fkey(updated_by)",
        "review_decisions.review_decisions_content_version_id_fkey(content_version_id)",
        "review_decisions.review_decisions_reviewer_id_fkey(reviewer_id)",
        "spend_logs.spend_logs_content_item_id_fkey(content_item_id)",
        "spend_reservations.spend_reservations_content_item_id_fkey(content_item_id)",
        "provider_usage.provider_usage_pipeline_stage_run_id_fkey(pipeline_stage_run_id)",
        "content_lineage.content_lineage_created_by_fkey(created_by)",
        "workflow_definitions.workflow_definitions_created_by_fkey(created_by)",
        "workflow_stages.workflow_stages_workspace_id_fkey(workspace_id)",
        "workflow_transitions.workflow_transitions_workspace_id_fkey(workspace_id)",
        "worker_registry.worker_registry_workspace_id_fkey(workspace_id)",
        "stage_assignments.stage_assignments_claimed_by_fkey(claimed_by)",
        "review_gates.review_gates_decided_by_fkey(decided_by)",
        "worker_credentials.worker_credentials_workspace_id_fkey(workspace_id)",
        "stage_claim_audit.stage_claim_audit_assignment_id_fkey(assignment_id)",
    }
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT
                  con.conrelid::regclass::text AS table_name,
                  con.conname,
                  array_agg(att.attname ORDER BY u.ord) AS fk_cols
                FROM pg_constraint con
                JOIN pg_namespace n ON n.oid = con.connamespace AND n.nspname = 'public'
                CROSS JOIN LATERAL unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
                JOIN pg_attribute att
                  ON att.attrelid = con.conrelid AND att.attnum = u.attnum
                WHERE con.contype = 'f'
                GROUP BY con.conrelid, con.conname
                """
            )
        )
        fks = list(rows)

        idx_rows = await s.execute(
            text(
                """
                SELECT
                  t.relname AS table_name,
                  array_agg(a.attname ORDER BY x.n) AS idx_cols
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace AND n.nspname = 'public'
                JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS x(attnum, n) ON true
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = x.attnum
                WHERE i.indisvalid AND a.attnum > 0
                GROUP BY t.relname, i.indexrelid
                """
            )
        )
        indexes_by_table: dict[str, list[list[str]]] = {}
        for table_name, idx_cols in idx_rows:
            indexes_by_table.setdefault(table_name, []).append(list(idx_cols))

    missing = []
    for table_name, conname, fk_cols in fks:
        fk_list = list(fk_cols)
        table_indexes = indexes_by_table.get(table_name, [])
        covered = any(idx[: len(fk_list)] == fk_list for idx in table_indexes)
        if not covered:
            missing.append(f"{table_name}.{conname}({','.join(fk_list)})")
    unexpected = sorted(set(missing) - known_gaps)
    obsolete = sorted(known_gaps - set(missing))
    assert not unexpected, f"new unindexed FKs (add indexes or update allowlist): {unexpected}"
    assert not obsolete, f"allowlist entries now indexed — remove from allowlist: {obsolete}"


@pytest.mark.asyncio
async def test_soft_delete_columns_present():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT table_name FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'deleted_at'
                """
            )
        )
        have = {r[0] for r in rows}
    missing = [t for t in SOFT_DELETE_TABLES if t not in have]
    assert not missing, f"soft-delete tables missing deleted_at: {missing}"


@pytest.mark.asyncio
async def test_optimistic_concurrency_version_columns():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT table_name FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'version'
                """
            )
        )
        have = {r[0] for r in rows}
    missing = [t for t in OPTIMISTIC_VERSION_TABLES if t not in have]
    assert not missing, f"version column missing: {missing}"


@pytest.mark.asyncio
async def test_idempotency_unique_indexes_exist_for_key_tables():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT tablename, indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' AND indexdef ILIKE '%idempotency_key%'
                """
            )
        )
        defs = list(rows)
    assert defs, "expected at least one idempotency_key index"
    assert any("UNIQUE" in d[2].upper() for d in defs), f"no UNIQUE idempotency index: {defs}"


@pytest.mark.asyncio
async def test_immutable_tables_listed_have_prevent_update_trigger():
    async with AsyncSessionLocal() as s:
        rows = await s.execute(
            text(
                """
                SELECT event_object_table, trigger_name
                FROM information_schema.triggers
                WHERE trigger_schema = 'public'
                  AND event_manipulation = 'UPDATE'
                """
            )
        )
        by_table: dict[str, set[str]] = {}
        for table, trig in rows:
            by_table.setdefault(table, set()).add(trig)
    missing = []
    for table in IMMUTABLE_TABLES:
        names = " ".join(by_table.get(table, set())).lower()
        if "immutable" not in names and "prevent_update" not in names:
            # accept any trigger that documents immutability in name
            if not by_table.get(table):
                missing.append(table)
            elif not any("prevent" in n or "immut" in n for n in by_table[table]):
                missing.append(f"{table}:{sorted(by_table[table])}")
    assert not missing, f"immutable tables missing prevent-update trigger: {missing}"
