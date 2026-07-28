"""P-009 / TD-022: widen spend_caps USD scale to match estimates.

Revision ID: 0031_spend_precision
Revises: 0030
Create Date: 2026-07-28

spend_logs / spend_reservations already use numeric(10,4). Caps were
numeric(10,2), so PATCH 0.005 rounded to 0.01 and near-zero policies
could not be expressed. Align caps to numeric(12,4).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_spend_precision"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE spend_caps
            ALTER COLUMN daily_cap_usd TYPE numeric(12,4)
                USING daily_cap_usd::numeric(12,4),
            ALTER COLUMN monthly_cap_usd TYPE numeric(12,4)
                USING monthly_cap_usd::numeric(12,4);
        """
    )


def downgrade() -> None:
    # Rounds back to 2 decimal places — documented data loss for sub-cent caps.
    op.execute(
        """
        ALTER TABLE spend_caps
            ALTER COLUMN daily_cap_usd TYPE numeric(10,2)
                USING round(daily_cap_usd, 2)::numeric(10,2),
            ALTER COLUMN monthly_cap_usd TYPE numeric(10,2)
                USING round(monthly_cap_usd, 2)::numeric(10,2);
        """
    )
