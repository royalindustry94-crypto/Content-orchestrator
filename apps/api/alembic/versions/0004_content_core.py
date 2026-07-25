"""Milestone 3: content core (content_items, content_versions)

Revision ID: 0004
Revises: 0003
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
    policy_insert_roles,
    policy_select_members,
    policy_update_roles,
)

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE content_stage AS ENUM ('idea','scripting','voiceover','visuals','rendering','seo','review','scheduled','published');")
    op.execute("CREATE TYPE content_status AS ENUM ('active','failed','archived');")
    op.execute(
        """
        CREATE TABLE content_items (
            id                      uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id            uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            pillar_id               uuid REFERENCES content_pillars(id),
            topic                   text NOT NULL,
            target_length_seconds   integer CHECK (target_length_seconds > 0),
            current_stage           content_stage NOT NULL DEFAULT 'idea',
            status                  content_status NOT NULL DEFAULT 'active',
            current_version_id      uuid,
            current_pipeline_run_id uuid,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            created_by              uuid REFERENCES profiles(id),
            updated_by              uuid REFERENCES profiles(id),
            version                 integer NOT NULL DEFAULT 1,
            deleted_at              timestamptz
        );
        """
    )
    op.execute("CREATE INDEX ix_content_items_workspace_stage ON content_items (workspace_id, current_stage) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_content_items_workspace_pillar ON content_items (workspace_id, pillar_id) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_content_items_workspace_status ON content_items (workspace_id, status) WHERE deleted_at IS NULL;")
    attach_version_trigger("content_items")
    enable_rls("content_items")
    grant_runtime("content_items")
    policy_select_members("content_items", _ALL, soft_delete=True)
    policy_insert_roles("content_items", _EDIT)
    policy_update_roles("content_items", _EDIT)

    op.execute(
        """
        CREATE TABLE content_versions (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            script_hook     text,
            script_body     text,
            script_cta      text,
            prompt_used     text,
            generated_by    text,
            created_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id)
        );
        """
    )
    op.execute("CREATE INDEX ix_content_versions_item ON content_versions (content_item_id, created_at DESC);")
    op.execute("CREATE INDEX ix_content_versions_workspace ON content_versions (workspace_id);")
    attach_immutable_trigger("content_versions")
    enable_rls("content_versions")
    grant_runtime("content_versions", update=False, delete=False)
    policy_select_members("content_versions", _ALL)
    policy_insert_roles("content_versions", _EDIT)

    op.execute("ALTER TABLE content_items ADD CONSTRAINT fk_content_items_current_version FOREIGN KEY (current_version_id) REFERENCES content_versions(id);")


def downgrade() -> None:
    op.execute("ALTER TABLE content_items DROP CONSTRAINT IF EXISTS fk_content_items_current_version;")
    op.execute("DROP TABLE IF EXISTS content_versions;")
    op.execute("DROP TABLE IF EXISTS content_items;")
    op.execute("DROP TYPE IF EXISTS content_status;")
    op.execute("DROP TYPE IF EXISTS content_stage;")
