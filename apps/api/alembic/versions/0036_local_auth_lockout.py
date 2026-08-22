"""Brute-force lockout state for AUTH_MODE=local credentials (M-F).

Adds durable failed-attempt accounting so repeated password guesses against
``/auth/login`` are throttled in the database rather than only in process
memory (which is per-replica and lost on restart).

Revision ID: 0036
Revises: 0035
Create Date: 2026-08-19
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "local_auth_credentials",
        sa.Column(
            "failed_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.add_column(
        "local_auth_credentials",
        sa.Column("last_failed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "local_auth_credentials",
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("local_auth_credentials", "locked_until")
    op.drop_column("local_auth_credentials", "last_failed_at")
    op.drop_column("local_auth_credentials", "failed_attempts")
