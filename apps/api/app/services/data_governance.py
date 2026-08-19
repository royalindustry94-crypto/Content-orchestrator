"""Workspace-scoped data export and deletion (data-governance controls).

Two operations, both admin-only and both explicitly bounded:

**Export** — returns the requesting workspace's own records only. Tables that
hold credentials or service-only material are on a hard denylist and are never
exported; the bundle names every omission so the caller cannot mistake a
partial bundle for a complete one.

**Deletion** — removes customer content for a workspace while preserving
records that must survive for accountability (spend, billing, review
decisions, audit trails). The preserved classes are returned explicitly, so a
deletion request is never silently over- or under-fulfilled.

Design rules that this module deliberately enforces:

* Table lists are explicit, not derived by reflection: a future table must be
  classified on purpose, and ``verify_table_classification`` fails a test if
  any workspace-scoped table is left unclassified.
* Both operations run on a caller-supplied session so they inherit that
  session's transaction; the caller commits.
* Nothing here bypasses RLS on its own; the API layer enforces admin
  authorization before calling in.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Tables that may never appear in a customer export bundle: they hold
# credentials, credential hashes, or service-only operational material.
EXPORT_DENYLIST: frozenset[str] = frozenset(
    {
        "provider_credentials",
        "worker_credentials",  # worker secret hashes
        "local_auth_credentials",
        "billing_webhook_events",  # raw third-party payloads
        "outbox_events",
        "event_consumers",
        "consumer_checkpoints",
        "provider_effect_keys",
    }
)

# Workspace-scoped tables that are exported to the owning workspace.
EXPORTABLE_TABLES: tuple[str, ...] = (
    "workspaces",
    "workspace_memberships",
    "content_pillars",
    "content_items",
    "content_versions",
    "content_lineage",
    "pipeline_runs",
    "pipeline_stage_runs",
    "review_gates",
    "review_decisions",
    "publication_eligibility",
    "assets",
    "publish_jobs",
    "analytics_snapshots",
    "provider_usage",
    "spend_caps",
    "spend_logs",
    "spend_reservations",
    "workspace_billing",
    "job_schedule",
    "workspace_concurrency_limits",
    "provider_concurrency_budgets",
    "workspace_backpressure_state",
    "stage_assignments",
    "stage_claim_audit",
    "stage_recovery_audit",
    "worker_registry",
    "worker_heartbeats",
    "worker_logs",
    "dead_letter_jobs",
    "webhook_events",
    "workflow_definitions",
    "workflow_stages",
    "workflow_transitions",
    "leads",
)

# Customer content tables that carry ``deleted_at`` and whose RLS grants the
# runtime role UPDATE (not DELETE). Withdrawing content is therefore a
# tombstone write, which is what the schema was designed for: dependent
# append-only rows (versions, lineage, analytics) keep referential integrity
# while the content stops being live. Granting DELETE here instead would
# require widening RLS and destroying append-only history.
SOFT_DELETABLE_TABLES: tuple[str, ...] = (
    "publish_jobs",
    "assets",
    "content_items",
    "content_pillars",
)

# Customer records with no append-only dependents and an explicit DELETE
# policy: removed outright.
HARD_DELETABLE_TABLES: tuple[str, ...] = (
    "publication_eligibility",
    "leads",
    "job_schedule",
)

DELETABLE_TABLES: tuple[str, ...] = SOFT_DELETABLE_TABLES + HARD_DELETABLE_TABLES

# Append-only children of withdrawn content. They are not deleted; they remain
# attached to a tombstoned parent. Reported explicitly so a deletion outcome is
# never ambiguous about them.
RETAINED_CONTENT_HISTORY_TABLES: tuple[str, ...] = (
    "content_versions",
    "content_lineage",
    "analytics_snapshots",
)

# Retained through a deletion request: financial, accountability, security and
# audit evidence. Deleting these would destroy the record of what happened.
RETAINED_ON_DELETE: tuple[str, ...] = (
    "spend_logs",
    "spend_reservations",
    "spend_caps",
    "provider_usage",
    "workspace_billing",
    "review_gates",
    "review_decisions",
    "stage_claim_audit",
    "stage_recovery_audit",
    "stage_assignments",
    "pipeline_stage_runs",
    "pipeline_runs",
    "worker_logs",
    "worker_heartbeats",
    "worker_registry",
    "worker_credentials",
    "dead_letter_jobs",
    "webhook_events",
    "billing_webhook_events",
    "outbox_events",
    "workflow_definitions",
    "workflow_stages",
    "workflow_transitions",
    "workspace_concurrency_limits",
    "provider_concurrency_budgets",
    "workspace_backpressure_state",
    "provider_credentials",
    "workspace_memberships",
    "workspaces",
)


class DataGovernanceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ExportBundle:
    workspace_id: uuid.UUID
    generated_at: datetime
    tables: dict[str, list[dict]]
    excluded_tables: tuple[str, ...]
    exclusion_reason: str
    row_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DeletionOutcome:
    workspace_id: uuid.UUID
    executed_at: datetime
    soft_deleted_counts: dict[str, int]
    hard_deleted_counts: dict[str, int]
    retained_content_history_tables: tuple[str, ...]
    retained_tables: tuple[str, ...]
    retention_reason: str


async def _existing_tables(session: AsyncSession) -> set[str]:
    rows = (
        await session.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
        )
    ).all()
    return {r[0] for r in rows}


async def _table_has_workspace_column(session: AsyncSession, table: str) -> bool:
    found = (
        await session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_schema='public' AND table_name=:t "
                "AND column_name='workspace_id'"
            ),
            {"t": table},
        )
    ).first()
    return found is not None


async def export_workspace(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> ExportBundle:
    """Export the workspace's own eligible records.

    Credential and service-only tables are excluded by name and reported.
    """
    present = await _existing_tables(session)
    tables: dict[str, list[dict]] = {}
    counts: dict[str, int] = {}

    for table in EXPORTABLE_TABLES:
        if table in EXPORT_DENYLIST:  # defensive: never export a denied table
            continue
        if table not in present:
            continue
        if table == "workspaces":
            stmt = text("SELECT * FROM workspaces WHERE id = :ws")
        elif await _table_has_workspace_column(session, table):
            stmt = text(f"SELECT * FROM {table} WHERE workspace_id = :ws")  # noqa: S608
        else:
            continue
        rows = (await session.execute(stmt, {"ws": str(workspace_id)})).mappings().all()
        serialised = [
            {k: (str(v) if isinstance(v, uuid.UUID | datetime) else v) for k, v in row.items()}
            for row in rows
        ]
        tables[table] = serialised
        counts[table] = len(serialised)

    return ExportBundle(
        workspace_id=workspace_id,
        generated_at=datetime.now(UTC),
        tables=tables,
        excluded_tables=tuple(sorted(EXPORT_DENYLIST)),
        exclusion_reason=(
            "Excluded by policy: these tables hold credentials, credential "
            "hashes, or service-only operational records and are never "
            "included in a customer export."
        ),
        row_counts=counts,
    )


async def delete_workspace_content(
    session: AsyncSession, *, workspace_id: uuid.UUID, confirm_workspace_id: uuid.UUID
) -> DeletionOutcome:
    """Delete customer content for a workspace, preserving audit evidence.

    ``confirm_workspace_id`` must equal ``workspace_id``: the caller has to
    restate the target, so a mis-routed request cannot delete another
    workspace's content.
    """
    if confirm_workspace_id != workspace_id:
        raise DataGovernanceError(
            "confirmation_mismatch",
            "deletion confirmation does not match the target workspace",
        )

    present = await _existing_tables(session)
    soft_deleted: dict[str, int] = {}
    hard_deleted: dict[str, int] = {}

    for table in SOFT_DELETABLE_TABLES:
        if table not in present:
            continue
        if not await _table_has_workspace_column(session, table):
            continue
        result = await session.execute(
            text(  # noqa: S608
                f"UPDATE {table} SET deleted_at = now() "
                "WHERE workspace_id = :ws AND deleted_at IS NULL"
            ),
            {"ws": str(workspace_id)},
        )
        soft_deleted[table] = int(result.rowcount or 0)

    for table in HARD_DELETABLE_TABLES:
        if table not in present:
            continue
        if not await _table_has_workspace_column(session, table):
            continue
        result = await session.execute(
            text(f"DELETE FROM {table} WHERE workspace_id = :ws"),  # noqa: S608
            {"ws": str(workspace_id)},
        )
        hard_deleted[table] = int(result.rowcount or 0)

    return DeletionOutcome(
        workspace_id=workspace_id,
        executed_at=datetime.now(UTC),
        soft_deleted_counts=soft_deleted,
        hard_deleted_counts=hard_deleted,
        retained_content_history_tables=RETAINED_CONTENT_HISTORY_TABLES,
        retained_tables=RETAINED_ON_DELETE,
        retention_reason=(
            "Content is withdrawn by tombstone where the schema is "
            "append-only, and financial, review, security and audit records "
            "are retained: deleting them would destroy the evidence of what "
            "was executed. Physical erasure of retained classes requires an "
            "approved retention schedule and legal basis."
        ),
    )


async def verify_table_classification(session: AsyncSession) -> list[str]:
    """Return workspace-scoped tables that are not classified anywhere.

    Used by tests: a new workspace-scoped table must be deliberately placed on
    the export list, the deletable list, the retained list, or the denylist.
    """
    rows = (
        await session.execute(
            text(
                "SELECT DISTINCT table_name FROM information_schema.columns "
                "WHERE table_schema='public' AND column_name='workspace_id'"
            )
        )
    ).all()
    classified = (
        set(EXPORTABLE_TABLES)
        | set(DELETABLE_TABLES)
        | set(RETAINED_CONTENT_HISTORY_TABLES)
        | set(RETAINED_ON_DELETE)
        | set(EXPORT_DENYLIST)
    )
    return sorted({r[0] for r in rows} - classified)
