"""Milestone 4: stage_assignments

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_version_trigger,
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE stage_assignment_status AS ENUM "
               "('pending','dispatched','acknowledged','completed','failed','cancelled');")
    op.execute(
        """
        CREATE TABLE stage_assignments (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id  uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            stage            content_stage NOT NULL,
            attempt_number   integer NOT NULL DEFAULT 1,
            worker_id        uuid REFERENCES worker_registry(id),
            status           stage_assignment_status NOT NULL DEFAULT 'pending',
            idempotency_key  text,
            lease_expires_at timestamptz,
            dispatched_at    timestamptz,
            acknowledged_at  timestamptz,
            completed_at     timestamptz,
            result           jsonb,
            correlation_id   uuid,
            trace_id         text,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_stage_assignments_workspace_idem "
               "ON stage_assignments (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;")
    # Reaper's query: dispatched/acknowledged rows whose lease expired.
    op.execute("CREATE INDEX ix_stage_assignments_lease ON stage_assignments (lease_expires_at) "
               "WHERE status IN ('dispatched','acknowledged');")
    # Dispatcher/worker poll: pending assignments matching a stage.
    op.execute("CREATE INDEX ix_stage_assignments_pending_stage ON stage_assignments (stage, created_at) "
               "WHERE status = 'pending';")
    op.execute("CREATE INDEX ix_stage_assignments_run ON stage_assignments (pipeline_run_id);")
    op.execute("CREATE INDEX ix_stage_assignments_worker ON stage_assignments (worker_id) "
               "WHERE worker_id IS NOT NULL;")
    attach_version_trigger("stage_assignments")
    enable_rls("stage_assignments")
    grant_runtime("stage_assignments")
    policy_select_members("stage_assignments", _ALL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS stage_assignments;")
    op.execute("DROP TYPE IF EXISTS stage_assignment_status;")
