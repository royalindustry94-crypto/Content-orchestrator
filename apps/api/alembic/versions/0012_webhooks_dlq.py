"""Milestone 3: webhook_events, dead_letter_jobs

Revision ID: 0012
Revises: 0011
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
    policy_select_members,
)

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADMIN_EDITOR = ["admin", "editor"]


def upgrade() -> None:
    op.execute("CREATE TYPE webhook_status AS ENUM ('received','processed','failed','duplicate');")
    op.execute(
        """
        CREATE TABLE webhook_events (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            source             text NOT NULL,
            external_event_id  text NOT NULL,
            signature_verified boolean NOT NULL,
            payload            jsonb NOT NULL,
            status             webhook_status NOT NULL DEFAULT 'received',
            received_at        timestamptz,
            processed_at       timestamptz,
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            version            integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_webhook_source_event UNIQUE (source, external_event_id)
        );
        """
    )
    op.execute("CREATE INDEX ix_webhook_events_status ON webhook_events (status) WHERE status IN ('received','failed');")
    op.execute("CREATE INDEX ix_webhook_events_workspace ON webhook_events (workspace_id);")
    attach_version_trigger("webhook_events")
    enable_rls("webhook_events")
    # System-written (worker); end users with admin/editor may read only.
    grant_runtime("webhook_events", insert=False, update=False, delete=False)
    policy_select_members("webhook_events", _ADMIN_EDITOR)

    op.execute("CREATE TYPE dead_letter_status AS ENUM ('pending','resolved','discarded');")
    op.execute(
        """
        CREATE TABLE dead_letter_jobs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            related_table   text NOT NULL,
            related_id      uuid NOT NULL,
            job_type        text NOT NULL,
            payload         jsonb,
            failure_reason  text NOT NULL,
            attempt_count   integer NOT NULL CHECK (attempt_count >= 1),
            first_failed_at timestamptz NOT NULL,
            last_failed_at  timestamptz NOT NULL,
            status          dead_letter_status NOT NULL DEFAULT 'pending',
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE INDEX ix_dead_letter_workspace_status ON dead_letter_jobs (workspace_id, status) WHERE status = 'pending';")
    op.execute("CREATE INDEX ix_dead_letter_related ON dead_letter_jobs (related_table, related_id);")
    attach_version_trigger("dead_letter_jobs")
    enable_rls("dead_letter_jobs")
    grant_runtime("dead_letter_jobs", insert=False, update=False, delete=False)
    policy_select_members("dead_letter_jobs", _ADMIN_EDITOR)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS dead_letter_jobs;")
    op.execute("DROP TYPE IF EXISTS dead_letter_status;")
    op.execute("DROP TABLE IF EXISTS webhook_events;")
    op.execute("DROP TYPE IF EXISTS webhook_status;")
