"""Milestone 3: pipeline (pipeline_runs, pipeline_stage_runs)

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_trigger,
    attach_version_trigger,
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE pipeline_run_status AS ENUM ('running','succeeded','failed','cancelled');")
    op.execute("CREATE TYPE stage_run_status AS ENUM ('succeeded','failed');")
    op.execute(
        """
        CREATE TABLE pipeline_runs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            current_stage   content_stage NOT NULL DEFAULT 'idea',
            status          pipeline_run_status NOT NULL DEFAULT 'running',
            started_at      timestamptz,
            completed_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE INDEX ix_pipeline_runs_item ON pipeline_runs (content_item_id, created_at DESC);")
    op.execute("CREATE INDEX ix_pipeline_runs_workspace_running ON pipeline_runs (workspace_id, status) WHERE status = 'running';")
    attach_version_trigger("pipeline_runs")
    enable_rls("pipeline_runs")
    grant_runtime("pipeline_runs")
    policy_select_members("pipeline_runs", _ALL)

    op.execute(
        """
        CREATE TABLE pipeline_stage_runs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            stage           content_stage NOT NULL,
            attempt_number  integer NOT NULL CHECK (attempt_number >= 1),
            status          stage_run_status NOT NULL,
            provider        text,
            cost_usd        numeric(10,4) CHECK (cost_usd >= 0),
            error_message   text,
            started_at      timestamptz,
            completed_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_stage_run_attempt UNIQUE (pipeline_run_id, stage, attempt_number)
        );
        """
    )
    op.execute("CREATE INDEX ix_stage_runs_run_stage ON pipeline_stage_runs (pipeline_run_id, stage);")
    op.execute("CREATE INDEX ix_stage_runs_workspace_status ON pipeline_stage_runs (workspace_id, status);")
    attach_immutable_trigger("pipeline_stage_runs")
    enable_rls("pipeline_stage_runs")
    grant_runtime("pipeline_stage_runs", update=False, delete=False)
    policy_select_members("pipeline_stage_runs", _ALL)

    op.execute("ALTER TABLE content_items ADD CONSTRAINT fk_content_items_current_run FOREIGN KEY (current_pipeline_run_id) REFERENCES pipeline_runs(id);")


def downgrade() -> None:
    op.execute("ALTER TABLE content_items DROP CONSTRAINT IF EXISTS fk_content_items_current_run;")
    op.execute("DROP TABLE IF EXISTS pipeline_stage_runs;")
    op.execute("DROP TABLE IF EXISTS pipeline_runs;")
    op.execute("DROP TYPE IF EXISTS stage_run_status;")
    op.execute("DROP TYPE IF EXISTS pipeline_run_status;")
