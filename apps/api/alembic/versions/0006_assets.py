"""Milestone 3: assets

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence, Union

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_version_trigger, enable_rls, grant_runtime,
    policy_insert_roles, policy_select_members, policy_update_roles,
)

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE asset_type AS ENUM ('script','audio','visual','render');")
    op.execute("CREATE TYPE asset_source AS ENUM ('ai_generated','uploaded');")
    op.execute("CREATE TYPE asset_status AS ENUM ('pending','ready','failed');")
    op.execute(
        """
        CREATE TABLE assets (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            content_version_id uuid REFERENCES content_versions(id),
            type               asset_type NOT NULL,
            source             asset_source NOT NULL,
            status             asset_status NOT NULL DEFAULT 'pending',
            url                text,
            sequence_index     integer,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            created_by         uuid REFERENCES profiles(id),
            updated_by         uuid REFERENCES profiles(id),
            version            integer NOT NULL DEFAULT 1,
            deleted_at         timestamptz
        );
        """
    )
    op.execute("CREATE INDEX ix_assets_item_type ON assets (content_item_id, type) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_assets_workspace ON assets (workspace_id);")
    attach_version_trigger("assets")
    enable_rls("assets")
    grant_runtime("assets")
    policy_select_members("assets", _ALL, soft_delete=True)
    policy_insert_roles("assets", _EDIT)
    policy_update_roles("assets", _EDIT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS assets;")
    op.execute("DROP TYPE IF EXISTS asset_status;")
    op.execute("DROP TYPE IF EXISTS asset_source;")
    op.execute("DROP TYPE IF EXISTS asset_type;")
