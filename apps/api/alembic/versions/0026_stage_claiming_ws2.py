"""Milestone 4 Workstream 2: job queue & atomic claiming.

Adds claim bookkeeping to stage_assignments, a workspace-scoped claim
poll index, and an append-only stage_claim_audit ledger (FORCE-RLS,
member-readable, service-role-written).

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-26
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    # --- claim bookkeeping on stage_assignments -------------------------------
    op.execute(
        """
        ALTER TABLE stage_assignments
            ADD COLUMN claimed_at  timestamptz,
            ADD COLUMN claimed_by  uuid REFERENCES worker_registry(id),
            ADD COLUMN claim_count integer NOT NULL DEFAULT 0,
            ADD COLUMN claim_token uuid;
        """
    )
    op.execute(
        "ALTER TABLE stage_assignments "
        "ADD CONSTRAINT ck_stage_assignments_claimed_by_matches "
        "CHECK (claimed_by IS NULL OR claimed_by = worker_id);"
    )
    # Workspace-scoped claim poll: matches predicate (workspace_id, stage,
    # status='pending') and order (created_at) exactly.
    op.execute(
        "CREATE INDEX ix_stage_assignments_claim "
        "ON stage_assignments (workspace_id, stage, created_at) "
        "WHERE status = 'pending';"
    )

    # --- claim audit ledger ---------------------------------------------------
    op.execute(
        "CREATE TYPE claim_outcome AS ENUM "
        "('granted','no_work','capacity','ineligible');"
    )
    op.execute(
        """
        CREATE TABLE stage_claim_audit (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id   uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id  uuid REFERENCES stage_assignments(id) ON DELETE SET NULL,
            worker_id      uuid NOT NULL REFERENCES worker_registry(id),
            outcome        claim_outcome NOT NULL,
            stage          content_stage,
            detail         text,
            correlation_id uuid,
            created_at     timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_stage_claim_audit_ws_created "
        "ON stage_claim_audit (workspace_id, created_at);"
    )
    op.execute(
        "CREATE INDEX ix_stage_claim_audit_worker "
        "ON stage_claim_audit (worker_id, created_at);"
    )
    enable_rls("stage_claim_audit")
    # Members may READ their workspace's ledger; writes are service-role only
    # (no INSERT/UPDATE/DELETE grant, no permissive fallback policy) — a claim
    # is written by the machine path under the service role, never by a tenant.
    grant_runtime("stage_claim_audit", insert=False, update=False, delete=False)
    policy_select_members("stage_claim_audit", _ALL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stage_claim_audit;")
    op.execute("DROP TYPE IF EXISTS claim_outcome;")
    op.execute("DROP INDEX IF EXISTS ix_stage_assignments_claim;")
    op.execute(
        "ALTER TABLE stage_assignments "
        "DROP CONSTRAINT IF EXISTS ck_stage_assignments_claimed_by_matches;"
    )
    op.execute(
        """
        ALTER TABLE stage_assignments
            DROP COLUMN IF EXISTS claim_token,
            DROP COLUMN IF EXISTS claim_count,
            DROP COLUMN IF EXISTS claimed_by,
            DROP COLUMN IF EXISTS claimed_at;
        """
    )
