"""Milestone 3: analytics_snapshots (immutable)

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_trigger, enable_rls, grant_runtime, policy_select_members,
)

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE analytics_snapshots (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            platform        text NOT NULL,
            metric          text NOT NULL,
            value           numeric NOT NULL,
            captured_at     timestamptz NOT NULL,
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_analytics_item_metric_time ON analytics_snapshots (content_item_id, metric, captured_at DESC);")
    op.execute("CREATE INDEX ix_analytics_workspace_time ON analytics_snapshots (workspace_id, captured_at DESC);")
    attach_immutable_trigger("analytics_snapshots")
    enable_rls("analytics_snapshots")
    grant_runtime("analytics_snapshots", update=False, delete=False)
    policy_select_members("analytics_snapshots", _ALL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS analytics_snapshots;")
