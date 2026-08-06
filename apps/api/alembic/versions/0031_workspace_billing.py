"""P-001 / WP-PB-004: workspace billing entitlements + webhook idempotency.

Revision ID: 0031
Revises: 0030
Create Date: 2026-07-28
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

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE workspace_billing (
            workspace_id            uuid PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
            stripe_customer_id      text UNIQUE,
            stripe_subscription_id  text UNIQUE,
            plan                    text NOT NULL DEFAULT 'none',
            status                  text NOT NULL DEFAULT 'inactive',
            current_period_end      timestamptz,
            cancel_at_period_end    boolean NOT NULL DEFAULT false,
            created_at              timestamptz NOT NULL DEFAULT now(),
            updated_at              timestamptz NOT NULL DEFAULT now(),
            version                 integer NOT NULL DEFAULT 1,
            CONSTRAINT workspace_billing_plan_chk
                CHECK (plan IN ('none', 'pro')),
            CONSTRAINT workspace_billing_status_chk
                CHECK (status IN (
                    'inactive', 'incomplete', 'trialing', 'active',
                    'past_due', 'canceled', 'unpaid'
                ))
        );
        """
    )
    attach_version_trigger("workspace_billing")
    enable_rls("workspace_billing")
    grant_runtime("workspace_billing", delete=False)
    policy_select_members("workspace_billing", _ALL)
    policy_insert_roles("workspace_billing", ["admin"])
    policy_update_roles("workspace_billing", ["admin"])

    # Webhook idempotency log — processed only by the API owner connection
    # (Stripe webhooks have no end-user JWT). FORCE RLS with no app_runtime
    # policies so request traffic cannot read/write this table.
    op.execute(
        """
        CREATE TABLE billing_webhook_events (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            stripe_event_id  text NOT NULL UNIQUE,
            event_type       text NOT NULL,
            workspace_id     uuid REFERENCES workspaces(id) ON DELETE SET NULL,
            processed_at     timestamptz NOT NULL DEFAULT now(),
            payload          jsonb NOT NULL DEFAULT '{}'::jsonb
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_billing_webhook_events_workspace ON billing_webhook_events (workspace_id);"
    )
    enable_rls("billing_webhook_events")
    # No GRANT to app_runtime — owner/migration role only.


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS billing_webhook_events;")
    op.execute("DROP TABLE IF EXISTS workspace_billing;")
