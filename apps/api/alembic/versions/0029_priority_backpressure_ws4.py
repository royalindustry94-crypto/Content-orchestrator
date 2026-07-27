"""Milestone 4 Workstream 4: priority queue, back-pressure, provider budgets.

Adds assignment priority/provider columns, workspace priority_tier,
queue soft/hard limits, workspace_backpressure_state, and
provider_concurrency_budgets. FORCE-RLS on new tables.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-27
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

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    # --- workspace tier -------------------------------------------------------
    op.execute(
        """
        ALTER TABLE workspaces
            ADD COLUMN priority_tier smallint NOT NULL DEFAULT 0;
        """
    )
    op.execute(
        "ALTER TABLE workspaces ADD CONSTRAINT ck_workspaces_priority_tier "
        "CHECK (priority_tier >= 0 AND priority_tier <= 10);"
    )

    # --- stage_assignments priority + provider --------------------------------
    op.execute(
        """
        ALTER TABLE stage_assignments
            ADD COLUMN priority integer NOT NULL DEFAULT 0,
            ADD COLUMN provider text;
        """
    )
    op.execute(
        """
        CREATE INDEX ix_stage_assignments_claim_priority
        ON stage_assignments (workspace_id, priority DESC, created_at ASC)
        WHERE status = 'pending'::stage_assignment_status;
        """
    )
    op.execute(
        """
        CREATE INDEX ix_stage_assignments_provider_inflight
        ON stage_assignments (workspace_id, provider)
        WHERE status = ANY (ARRAY[
            'dispatched'::stage_assignment_status,
            'acknowledged'::stage_assignment_status
        ])
        AND provider IS NOT NULL;
        """
    )

    # --- concurrency limit thresholds -----------------------------------------
    op.execute(
        """
        ALTER TABLE workspace_concurrency_limits
            ADD COLUMN queue_soft_limit integer NOT NULL DEFAULT 50,
            ADD COLUMN queue_hard_limit integer NOT NULL DEFAULT 200;
        """
    )
    op.execute(
        "ALTER TABLE workspace_concurrency_limits "
        "ADD CONSTRAINT ck_workspace_concurrency_queue_limits "
        "CHECK (queue_soft_limit > 0 AND queue_hard_limit >= queue_soft_limit);"
    )

    # --- back-pressure state --------------------------------------------------
    op.execute(
        "CREATE TYPE backpressure_state AS ENUM ('normal','pressured','throttled');"
    )
    op.execute(
        """
        CREATE TABLE workspace_backpressure_state (
            workspace_id   uuid PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
            state          backpressure_state NOT NULL DEFAULT 'normal',
            pending_depth  integer NOT NULL DEFAULT 0,
            entered_at     timestamptz,
            updated_at     timestamptz NOT NULL DEFAULT now(),
            version        integer NOT NULL DEFAULT 1
        );
        """
    )
    attach_version_trigger("workspace_backpressure_state")
    enable_rls("workspace_backpressure_state")
    grant_runtime("workspace_backpressure_state", insert=False, update=False, delete=False)
    policy_select_members("workspace_backpressure_state", _ALL)

    # --- provider concurrency budgets -----------------------------------------
    op.execute(
        """
        CREATE TABLE provider_concurrency_budgets (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider        text NOT NULL,
            max_concurrent  integer NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_provider_concurrency_budgets_ws_provider
                UNIQUE (workspace_id, provider),
            CONSTRAINT ck_provider_concurrency_budgets_max
                CHECK (max_concurrent > 0)
        );
        """
    )
    attach_version_trigger("provider_concurrency_budgets")
    enable_rls("provider_concurrency_budgets")
    grant_runtime("provider_concurrency_budgets", insert=False, update=False, delete=False)
    policy_select_members("provider_concurrency_budgets", _ALL)
    op.execute(
        "CREATE INDEX ix_provider_concurrency_budgets_ws "
        "ON provider_concurrency_budgets (workspace_id);"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provider_concurrency_budgets;")
    op.execute("DROP TABLE IF EXISTS workspace_backpressure_state;")
    op.execute("DROP TYPE IF EXISTS backpressure_state;")
    op.execute(
        "ALTER TABLE workspace_concurrency_limits "
        "DROP CONSTRAINT IF EXISTS ck_workspace_concurrency_queue_limits;"
    )
    op.execute(
        """
        ALTER TABLE workspace_concurrency_limits
            DROP COLUMN IF EXISTS queue_hard_limit,
            DROP COLUMN IF EXISTS queue_soft_limit;
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_stage_assignments_provider_inflight;")
    op.execute("DROP INDEX IF EXISTS ix_stage_assignments_claim_priority;")
    op.execute(
        """
        ALTER TABLE stage_assignments
            DROP COLUMN IF EXISTS provider,
            DROP COLUMN IF EXISTS priority;
        """
    )
    op.execute("ALTER TABLE workspaces DROP CONSTRAINT IF EXISTS ck_workspaces_priority_tier;")
    op.execute("ALTER TABLE workspaces DROP COLUMN IF EXISTS priority_tier;")
