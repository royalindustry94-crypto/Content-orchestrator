"""Operations Dashboard V2: workspace-scoped leads CRM.

Revision ID: 0034
Revises: 0033
Create Date: 2026-08-06
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

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]
_WRITE = ["admin", "editor"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE leads (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            name            text NOT NULL,
            company         text,
            email           text NOT NULL,
            source          text NOT NULL DEFAULT 'manual',
            status          text NOT NULL DEFAULT 'new',
            notes           text,
            follow_up_date  date,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT leads_status_chk CHECK (status IN (
                'new', 'contacted', 'qualified', 'negotiation',
                'won', 'lost', 'nurturing'
            )),
            CONSTRAINT leads_email_chk CHECK (position('@' in email) > 1)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_leads_workspace_status ON leads (workspace_id, status);"
    )
    op.execute(
        "CREATE INDEX ix_leads_workspace_follow_up ON leads (workspace_id, follow_up_date);"
    )
    op.execute(
        "CREATE INDEX ix_leads_workspace_email ON leads (workspace_id, email);"
    )
    attach_version_trigger("leads")
    enable_rls("leads")
    grant_runtime("leads")
    policy_select_members("leads", _ALL)
    policy_insert_roles("leads", _WRITE)
    policy_update_roles("leads", _WRITE)
    op.execute(
        """
        CREATE POLICY leads_delete_roles ON leads FOR DELETE
        USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS leads;")
