"""Add workspace_content_profiles: durable per-workspace business/audience/
brand-voice defaults, collected once (guided quick-setup or manual edit)
and reused as the default content-job authoring context.

Revision ID: 0055
Revises: 0054
Create Date: 2026-09-09

Onboarding gap (2026-09-09 recovery-audit follow-up, Founder-directed): a
new workspace previously had nothing to configure beyond its name and
spend caps — every "Business Manager" surface a first-time user sees
(Strategy, Content Department) reports `business_context_state:
"incomplete"` permanently, because no workspace-level settings existed to
complete it. This does not touch TD-041 (live-provider activation, still
separately gated) — Draft Desk's existing deterministic template
generation can already use these fields as defaults; nothing here claims
a live AI provider is connected.

Same RLS shape as `content_pillars` (migration 0003): editor/admin write,
admin/editor/reviewer read — matches `require_workspace_content_author`
in `app/core/authorization.py`, the same guard `content_jobs.py` uses.
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
    policy_update_roles,
)

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workspace_content_profiles (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            business_name    text,
            offer            text,
            target_audience  text,
            brand_voice      text,
            target_platform  text,
            content_goal     text,
            created_at       timestamptz NOT NULL DEFAULT now(),
            updated_at       timestamptz NOT NULL DEFAULT now(),
            created_by       uuid REFERENCES profiles(id),
            updated_by       uuid REFERENCES profiles(id),
            version          integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_workspace_content_profiles_workspace "
        "ON workspace_content_profiles (workspace_id);"
    )
    # Covering indexes for the created_by/updated_by FKs (P1-006 / TD-021
    # convention — every FK column gets one in the same migration that
    # creates the table now, rather than a follow-up migration later).
    op.execute(
        "CREATE INDEX ix_workspace_content_profiles_created_by "
        "ON workspace_content_profiles (created_by);"
    )
    op.execute(
        "CREATE INDEX ix_workspace_content_profiles_updated_by "
        "ON workspace_content_profiles (updated_by);"
    )
    attach_version_trigger("workspace_content_profiles")
    enable_rls("workspace_content_profiles")
    grant_runtime("workspace_content_profiles")
    policy_select_members("workspace_content_profiles", _ALL)
    policy_insert_roles("workspace_content_profiles", _EDIT)
    policy_update_roles("workspace_content_profiles", _EDIT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS workspace_content_profiles;")
