"""Milestone 4: workflow_definitions, workflow_stages, workflow_transitions

Also ALTERs pipeline_run_status to add 'created', 'paused', 'compensating'
(needed by the orchestration engine's fuller run lifecycle) and adds the
paused-run bookkeeping columns to pipeline_runs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_trigger, attach_version_trigger, enable_rls, grant_runtime,
    policy_all_roles, policy_insert_roles, policy_select_members,
)

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    # Extend the pipeline run lifecycle for the orchestration engine.
    op.execute("ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'created';")
    op.execute("ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'paused';")
    op.execute("ALTER TYPE pipeline_run_status ADD VALUE IF NOT EXISTS 'compensating';")
    op.execute(
        """
        ALTER TABLE pipeline_runs
            ADD COLUMN pause_reason text,
            ADD COLUMN definition_id uuid,
            ADD COLUMN correlation_id uuid,
            ADD COLUMN trace_id text;
        """
    )

    op.execute("CREATE TYPE workflow_transition_trigger AS ENUM "
               "('on_success','on_failure','on_review_approved','on_review_rejected');")

    op.execute(
        """
        CREATE TABLE workflow_definitions (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name         text NOT NULL,
            version      integer NOT NULL,
            is_active    boolean NOT NULL DEFAULT true,
            created_at   timestamptz NOT NULL DEFAULT now(),
            created_by   uuid REFERENCES profiles(id),
            CONSTRAINT uq_workflow_definition_version UNIQUE (workspace_id, name, version)
        );
        """
    )
    op.execute("CREATE INDEX ix_workflow_definitions_active "
               "ON workflow_definitions (workspace_id, name) WHERE is_active;")
    attach_immutable_trigger("workflow_definitions")
    enable_rls("workflow_definitions")
    grant_runtime("workflow_definitions", update=False, delete=False)
    policy_select_members("workflow_definitions", _ALL)
    policy_insert_roles("workflow_definitions", ["admin"])

    op.execute(
        """
        CREATE TABLE workflow_stages (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id           uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            definition_id          uuid NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
            stage_key              content_stage NOT NULL,
            ordinal                integer NOT NULL,
            max_attempts           integer NOT NULL DEFAULT 3,
            backoff_base_seconds   integer NOT NULL DEFAULT 5,
            backoff_multiplier     integer NOT NULL DEFAULT 2,
            backoff_max_seconds    integer NOT NULL DEFAULT 300,
            timeout_seconds        integer NOT NULL DEFAULT 600,
            is_review_gate         boolean NOT NULL DEFAULT false,
            is_terminal            boolean NOT NULL DEFAULT false,
            compensation_stage_key content_stage,
            created_at             timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_workflow_stage_per_definition UNIQUE (definition_id, stage_key)
        );
        """
    )
    op.execute("CREATE INDEX ix_workflow_stages_definition ON workflow_stages (definition_id, ordinal);")
    attach_immutable_trigger("workflow_stages")
    enable_rls("workflow_stages")
    grant_runtime("workflow_stages", update=False, delete=False)
    policy_select_members("workflow_stages", _ALL)
    policy_insert_roles("workflow_stages", ["admin"])

    op.execute(
        """
        CREATE TABLE workflow_transitions (
            id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id   uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            definition_id  uuid NOT NULL REFERENCES workflow_definitions(id) ON DELETE CASCADE,
            from_stage     content_stage NOT NULL,
            to_stage       content_stage NOT NULL,
            trigger        workflow_transition_trigger NOT NULL,
            condition      jsonb,
            priority       integer NOT NULL DEFAULT 0,
            created_at     timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_workflow_transitions_lookup "
               "ON workflow_transitions (definition_id, from_stage, trigger);")
    attach_immutable_trigger("workflow_transitions")
    enable_rls("workflow_transitions")
    grant_runtime("workflow_transitions", update=False, delete=False)
    policy_select_members("workflow_transitions", _ALL)
    policy_insert_roles("workflow_transitions", ["admin"])

    op.execute("ALTER TABLE pipeline_runs ADD CONSTRAINT fk_pipeline_runs_definition "
               "FOREIGN KEY (definition_id) REFERENCES workflow_definitions(id);")


def downgrade() -> None:
    op.execute("ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS fk_pipeline_runs_definition;")
    op.execute("DROP TABLE IF EXISTS workflow_transitions;")
    op.execute("DROP TABLE IF EXISTS workflow_stages;")
    op.execute("DROP TABLE IF EXISTS workflow_definitions;")
    op.execute("DROP TYPE IF EXISTS workflow_transition_trigger;")
    op.execute(
        "ALTER TABLE pipeline_runs "
        "DROP COLUMN IF EXISTS pause_reason, "
        "DROP COLUMN IF EXISTS definition_id, "
        "DROP COLUMN IF EXISTS correlation_id, "
        "DROP COLUMN IF EXISTS trace_id;"
    )
    # Note: Postgres cannot drop enum values; 'created'/'paused'/'compensating'
    # remain in pipeline_run_status on downgrade (documented, harmless no-op).
