"""Permit atomic app-runtime domain event writes under workspace role RLS.

The outbox has always granted INSERT to app_runtime because domain mutations
must write their corresponding durable event in the same transaction. Its
original RLS policy only allowed reads, which made authenticated runtime
transactions unable to emit events. This migration adds the same admin/editor
workspace role check used by other domain tables. No route exposes arbitrary
outbox insertion; all events still flow through the typed domain services.

Revision ID: 0042
Revises: 0041
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import policy_insert_roles  # noqa: E402

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    policy_insert_roles("outbox_events", ["admin", "editor"])


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS outbox_events_insert_roles ON outbox_events;")
