"""Milestone 4: job_schedule, workspace_concurrency_limits (back-pressure)

Revision ID: 0016
Revises: 0015
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
    policy_insert_roles,
    policy_select_members,
    policy_update_roles,
)

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADMIN_EDITOR = ["admin", "editor"]


def upgrade() -> None:
    op.execute("CREATE TYPE job_type AS ENUM "
               "('stage','retry','stage_timeout','review_timeout','recurring','compensation');")
    op.execute("CREATE TYPE job_schedule_status AS ENUM ('pending','leased','done','cancelled');")

    op.execute(
        """
        CREATE TABLE job_schedule (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            job_type         job_type NOT NULL,
            ref_table        text NOT NULL,
            ref_id           uuid NOT NULL,
            run_after        timestamptz NOT NULL,
            status           job_schedule_status NOT NULL DEFAULT 'pending',
            lease_owner      text,
            lease_expires_at timestamptz,
            attempt          integer NOT NULL DEFAULT 0,
            priority         integer NOT NULL DEFAULT 0,
            correlation_id   uuid,
            trace_id         text,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );
        """
    )
    # The scheduler's core query: due, pending, ordered.
    op.execute("CREATE INDEX ix_job_schedule_due ON job_schedule (status, run_after) "
               "WHERE status = 'pending';")
    # Reaper's query: leased rows whose lease has expired.
    op.execute("CREATE INDEX ix_job_schedule_lease_expiry ON job_schedule (lease_expires_at) "
               "WHERE status = 'leased';")
    # Fairness: per-workspace due-work lookup for weighted round-robin.
    op.execute("CREATE INDEX ix_job_schedule_workspace_due ON job_schedule (workspace_id, run_after) "
               "WHERE status = 'pending';")
    attach_version_trigger("job_schedule")
    enable_rls("job_schedule")
    grant_runtime("job_schedule")
    policy_select_members("job_schedule", _ADMIN_EDITOR)

    op.execute(
        """
        CREATE TABLE workspace_concurrency_limits (
            id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id              uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            max_concurrent_assignments integer NOT NULL DEFAULT 10,
            max_per_scheduler_tick    integer NOT NULL DEFAULT 5,
            created_at                timestamptz NOT NULL DEFAULT now(),
            updated_at                timestamptz NOT NULL DEFAULT now(),
            version                   integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_workspace_concurrency_limit UNIQUE (workspace_id)
        );
        """
    )
    attach_version_trigger("workspace_concurrency_limits")
    enable_rls("workspace_concurrency_limits")
    grant_runtime("workspace_concurrency_limits")
    policy_select_members("workspace_concurrency_limits", _ADMIN_EDITOR)
    policy_insert_roles("workspace_concurrency_limits", ["admin"])
    policy_update_roles("workspace_concurrency_limits", ["admin"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_concurrency_limits;")
    op.execute("DROP TABLE IF EXISTS job_schedule;")
    op.execute("DROP TYPE IF EXISTS job_schedule_status;")
    op.execute("DROP TYPE IF EXISTS job_type;")
