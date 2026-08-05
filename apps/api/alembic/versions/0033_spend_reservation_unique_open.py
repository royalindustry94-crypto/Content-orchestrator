"""Partial unique index: one open spend reservation per (run, stage).

Revision ID: 0033
Revises: 0032_merge_p1
Create Date: 2026-08-05

Prevents duplicate RESERVED rows that break worker submit after retry/
recovery (PR #34 H-4). Existing duplicates are released before the index
is created.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0033"
down_revision: str | None = "0032_merge_p1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Keep the newest open reservation per (run, stage); release the rest.
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY pipeline_run_id, stage
                       ORDER BY created_at DESC, id DESC
                   ) AS rn
            FROM spend_reservations
            WHERE status = 'reserved'
              AND pipeline_run_id IS NOT NULL
              AND stage IS NOT NULL
        )
        UPDATE spend_reservations sr
        SET status = 'released',
            updated_at = now(),
            version = sr.version + 1
        FROM ranked
        WHERE sr.id = ranked.id
          AND ranked.rn > 1;
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX ux_spend_reservations_open_run_stage
        ON spend_reservations (pipeline_run_id, stage)
        WHERE status = 'reserved'
          AND pipeline_run_id IS NOT NULL
          AND stage IS NOT NULL;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_spend_reservations_open_run_stage;")
