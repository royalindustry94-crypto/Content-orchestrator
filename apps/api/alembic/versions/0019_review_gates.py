"""Milestone 4: review_gates

Revision ID: 0019
Revises: 0018
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
)

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE review_gate_status AS ENUM "
               "('awaiting','approved','rejected','timed_out','escalated');")
    op.execute(
        """
        CREATE TABLE review_gates (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pipeline_run_id  uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
            stage            content_stage NOT NULL,
            status           review_gate_status NOT NULL DEFAULT 'awaiting',
            requested_at     timestamptz NOT NULL DEFAULT now(),
            timeout_at       timestamptz,
            decided_at       timestamptz,
            decided_by       uuid REFERENCES profiles(id),
            escalation_level integer NOT NULL DEFAULT 0,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            version          integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE INDEX ix_review_gates_run ON review_gates (pipeline_run_id);")
    op.execute("CREATE INDEX ix_review_gates_awaiting_timeout ON review_gates (timeout_at) "
               "WHERE status = 'awaiting';")
    op.execute("CREATE INDEX ix_review_gates_workspace_status ON review_gates (workspace_id, status);")
    attach_version_trigger("review_gates")
    enable_rls("review_gates")
    grant_runtime("review_gates")
    policy_select_members("review_gates", _ALL)
    policy_insert_roles("review_gates", ["admin", "reviewer"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_gates;")
    op.execute("DROP TYPE IF EXISTS review_gate_status;")
