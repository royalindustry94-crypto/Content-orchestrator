"""Milestone 3: publish_jobs

Revision ID: 0007
Revises: 0006
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

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute("CREATE TYPE publish_job_status AS ENUM ('pending','publishing','published','failed','cancelled');")
    op.execute(
        """
        CREATE TABLE publish_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            platform        text NOT NULL,
            scheduled_time  timestamptz NOT NULL,
            status          publish_job_status NOT NULL DEFAULT 'pending',
            external_post_id text,
            error_message   text,
            published_at    timestamptz,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            created_by      uuid REFERENCES profiles(id),
            updated_by      uuid REFERENCES profiles(id),
            version         integer NOT NULL DEFAULT 1,
            deleted_at      timestamptz
        );
        """
    )
    op.execute("CREATE INDEX ix_publish_jobs_workspace_time ON publish_jobs (workspace_id, scheduled_time) WHERE deleted_at IS NULL;")
    op.execute("CREATE INDEX ix_publish_jobs_workspace_status ON publish_jobs (workspace_id, status);")
    op.execute("CREATE INDEX ix_publish_jobs_item ON publish_jobs (content_item_id);")
    attach_version_trigger("publish_jobs")
    enable_rls("publish_jobs")
    grant_runtime("publish_jobs")
    policy_select_members("publish_jobs", _ALL, soft_delete=True)
    policy_insert_roles("publish_jobs", _EDIT)
    policy_update_roles("publish_jobs", _EDIT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS publish_jobs;")
    op.execute("DROP TYPE IF EXISTS publish_job_status;")
