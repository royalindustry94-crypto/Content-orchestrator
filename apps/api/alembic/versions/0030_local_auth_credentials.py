"""Local auth credentials for AUTH_MODE=local (Private Beta).

Revision ID: 0030
Revises: 0029
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "local_auth_credentials",
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("email", name="uq_local_auth_credentials_email"),
    )
    # Owner-only table for auth; runtime role needs SELECT/INSERT/UPDATE for login/signup.
    op.execute("GRANT SELECT, INSERT, UPDATE ON local_auth_credentials TO app_runtime;")
    # No RLS: credentials are looked up by email before a JWT exists. Access is
    # limited to the API process via APP_DATABASE_URL and never exposed via HTTP
    # except through hashed-password signup/login handlers.


def downgrade() -> None:
    op.drop_table("local_auth_credentials")
