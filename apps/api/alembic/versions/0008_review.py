"""Milestone 3: review_decisions (immutable)

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_trigger, enable_rls, grant_runtime,
    policy_insert_roles, policy_select_members,
)

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE review_decision_value AS ENUM ('approved','changes_requested','rejected');")
    op.execute(
        """
        CREATE TABLE review_decisions (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            content_version_id uuid REFERENCES content_versions(id),
            reviewer_id        uuid NOT NULL REFERENCES profiles(id),
            decision           review_decision_value NOT NULL,
            notes              text,
            created_at         timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_review_decisions_item ON review_decisions (content_item_id, created_at DESC);")
    op.execute("CREATE INDEX ix_review_decisions_workspace ON review_decisions (workspace_id);")
    attach_immutable_trigger("review_decisions")
    enable_rls("review_decisions")
    grant_runtime("review_decisions", update=False, delete=False)
    policy_select_members("review_decisions", _ALL)
    policy_insert_roles("review_decisions", ["admin", "reviewer"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS review_decisions;")
    op.execute("DROP TYPE IF EXISTS review_decision_value;")
