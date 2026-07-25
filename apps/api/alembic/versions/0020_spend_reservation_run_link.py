"""Milestone 4: link spend_reservations to the pipeline run that made them

Fixes a scoping gap surfaced while implementing the execution controller:
without a run reference, releasing "this run's open reservations" on
failure/cancel had no correct scope (content_item_id alone doesn't
distinguish between retried runs of the same content item).

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-21
"""
from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE spend_reservations ADD COLUMN pipeline_run_id uuid "
        "REFERENCES pipeline_runs(id) ON DELETE CASCADE;"
    )
    op.execute("CREATE INDEX ix_spend_reservations_run ON spend_reservations (pipeline_run_id) "
               "WHERE pipeline_run_id IS NOT NULL;")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_spend_reservations_run;")
    op.execute("ALTER TABLE spend_reservations DROP COLUMN IF EXISTS pipeline_run_id;")
