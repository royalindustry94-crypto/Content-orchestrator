"""Milestone 3: workspace config (content_pillars, spend_caps, provider_credentials)

Revision ID: 0003
Revises: 0002
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
    policy_all_roles, policy_insert_roles, policy_select_members, policy_update_roles,
)

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE content_pillars (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name         text NOT NULL,
            created_at   timestamptz NOT NULL DEFAULT now(),
            updated_at   timestamptz NOT NULL DEFAULT now(),
            created_by   uuid REFERENCES profiles(id),
            updated_by   uuid REFERENCES profiles(id),
            version      integer NOT NULL DEFAULT 1,
            deleted_at   timestamptz
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_content_pillars_workspace_name ON content_pillars (workspace_id, name) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_content_pillars_workspace ON content_pillars (workspace_id);")
    attach_version_trigger("content_pillars")
    enable_rls("content_pillars")
    grant_runtime("content_pillars")
    policy_select_members("content_pillars", _ALL, soft_delete=True)
    policy_insert_roles("content_pillars", _EDIT)
    policy_update_roles("content_pillars", _EDIT)

    op.execute(
        """
        CREATE TABLE spend_caps (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider        text,
            daily_cap_usd   numeric(10,2) NOT NULL CHECK (daily_cap_usd >= 0),
            monthly_cap_usd numeric(10,2) NOT NULL CHECK (monthly_cap_usd >= 0),
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id),
            updated_by      uuid REFERENCES profiles(id),
            version         integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_spend_caps_workspace_provider ON spend_caps (workspace_id, COALESCE(provider, ''));")
    attach_version_trigger("spend_caps")
    enable_rls("spend_caps")
    grant_runtime("spend_caps")
    policy_select_members("spend_caps", _ALL)
    policy_insert_roles("spend_caps", ["admin"])
    policy_update_roles("spend_caps", ["admin"])

    op.execute("CREATE TYPE provider_credential_status AS ENUM ('active', 'revoked');")
    op.execute(
        """
        CREATE TABLE provider_credentials (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            provider          text NOT NULL,
            label             text NOT NULL,
            encrypted_secret  text NOT NULL,
            encryption_key_id text NOT NULL,
            status            provider_credential_status NOT NULL DEFAULT 'active',
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            created_by        uuid REFERENCES profiles(id),
            updated_by        uuid REFERENCES profiles(id),
            version           integer NOT NULL DEFAULT 1,
            deleted_at        timestamptz
        );
        """
    )
    op.execute("CREATE UNIQUE INDEX uq_provider_credentials_workspace_provider_label ON provider_credentials (workspace_id, provider, label) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_provider_credentials_workspace ON provider_credentials (workspace_id);")
    attach_version_trigger("provider_credentials")
    enable_rls("provider_credentials")
    grant_runtime("provider_credentials")
    policy_all_roles("provider_credentials", ["admin"], policy_suffix="admin_only")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provider_credentials;")
    op.execute("DROP TYPE IF EXISTS provider_credential_status;")
    op.execute("DROP TABLE IF EXISTS spend_caps;")
    op.execute("DROP TABLE IF EXISTS content_pillars;")
