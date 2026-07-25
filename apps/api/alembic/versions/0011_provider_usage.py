"""Milestone 3: provider_usage (immutable)

Revision ID: 0011
Revises: 0010
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
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE provider_usage (
            id                    uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id          uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id       uuid REFERENCES content_items(id),
            pipeline_stage_run_id uuid REFERENCES pipeline_stage_runs(id),
            provider              text NOT NULL,
            operation             text,
            quantity              numeric NOT NULL,
            unit_type             text NOT NULL,
            occurred_at           timestamptz NOT NULL,
            created_at            timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_provider_usage_workspace_provider_time ON provider_usage (workspace_id, provider, occurred_at DESC);")
    op.execute("CREATE INDEX ix_provider_usage_item ON provider_usage (content_item_id) WHERE content_item_id IS NOT NULL;")
    attach_immutable_trigger("provider_usage")
    enable_rls("provider_usage")
    grant_runtime("provider_usage", update=False, delete=False)
    policy_select_members("provider_usage", _ALL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provider_usage;")
