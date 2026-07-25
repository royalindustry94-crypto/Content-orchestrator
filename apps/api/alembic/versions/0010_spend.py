"""Milestone 3: spend (spend_logs immutable, spend_reservations mutable)

Revision ID: 0010
Revises: 0009
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
    policy_select_members,
)

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE spend_logs (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id    uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id uuid REFERENCES content_items(id),
            provider        text NOT NULL,
            stage           content_stage,
            units           numeric,
            cost_usd        numeric(10,4) NOT NULL CHECK (cost_usd >= 0),
            occurred_at     timestamptz NOT NULL DEFAULT now(),
            created_at      timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_spend_logs_workspace_time ON spend_logs (workspace_id, occurred_at DESC);")
    op.execute("CREATE INDEX ix_spend_logs_workspace_provider_time ON spend_logs (workspace_id, provider, occurred_at DESC);")
    attach_immutable_trigger("spend_logs")
    enable_rls("spend_logs")
    grant_runtime("spend_logs", update=False, delete=False)
    policy_select_members("spend_logs", _ALL)

    op.execute("CREATE TYPE reservation_status AS ENUM ('reserved','committed','released');")
    op.execute(
        """
        CREATE TABLE spend_reservations (
            id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id       uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id    uuid REFERENCES content_items(id),
            provider           text NOT NULL,
            stage              content_stage,
            estimated_cost_usd numeric(10,4) NOT NULL CHECK (estimated_cost_usd >= 0),
            status             reservation_status NOT NULL DEFAULT 'reserved',
            created_at         timestamptz NOT NULL DEFAULT now(),
            updated_at         timestamptz NOT NULL DEFAULT now(),
            version            integer NOT NULL DEFAULT 1
        );
        """
    )
    op.execute("CREATE INDEX ix_spend_reservations_workspace_status ON spend_reservations (workspace_id, status) WHERE status = 'reserved';")
    attach_version_trigger("spend_reservations")
    enable_rls("spend_reservations")
    grant_runtime("spend_reservations")
    policy_select_members("spend_reservations", _ALL)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS spend_reservations;")
    op.execute("DROP TYPE IF EXISTS reservation_status;")
    op.execute("DROP TABLE IF EXISTS spend_logs;")
