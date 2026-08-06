"""Mission Control V4: durable workspace-scoped worker logs.

Revision ID: 0035
Revises: 0034
Create Date: 2026-08-06
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import enable_rls, grant_runtime, policy_select_members  # noqa: E402

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE worker_logs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            worker_id       uuid NOT NULL REFERENCES worker_registry(id) ON DELETE CASCADE,
            pipeline_run_id uuid REFERENCES pipeline_runs(id) ON DELETE SET NULL,
            assignment_id   uuid REFERENCES stage_assignments(id) ON DELETE SET NULL,
            severity        text NOT NULL,
            message         text NOT NULL,
            context         jsonb NOT NULL DEFAULT '{}'::jsonb,
            occurred_at     timestamptz NOT NULL DEFAULT now(),
            received_at     timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT worker_logs_severity_chk
                CHECK (severity IN ('debug', 'info', 'warning', 'error', 'critical'))
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_worker_logs_workspace_time "
        "ON worker_logs (workspace_id, occurred_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_worker_logs_worker_time "
        "ON worker_logs (worker_id, occurred_at DESC);"
    )
    op.execute(
        "CREATE INDEX ix_worker_logs_pipeline_time "
        "ON worker_logs (pipeline_run_id, occurred_at DESC) "
        "WHERE pipeline_run_id IS NOT NULL;"
    )
    op.execute(
        "CREATE INDEX ix_worker_logs_assignment_time "
        "ON worker_logs (assignment_id, occurred_at DESC) "
        "WHERE assignment_id IS NOT NULL;"
    )
    enable_rls("worker_logs")
    grant_runtime("worker_logs", insert=False, update=False, delete=False)
    policy_select_members("worker_logs", ["admin"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS worker_logs;")
