"""Bind each Human Review Gate to the exact immutable content version reviewed.

An approved gate previously identified a pipeline run and content item only.  If
that item's ``current_version_id`` changed after approval, publication policy
could still treat the old approval as valid.  This was independently reproduced
by replacing the current version after an approval and observing a successful
publication eligibility decision.

New gates capture the item current-version pointer when the review is opened.
The column remains nullable for existing historical rows; the publication gate
fails closed for a missing or non-current version rather than treating a legacy
approval as sufficient.  No existing migration is altered or renumbered.

Revision ID: 0040
Revises: 0039
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_gates",
        sa.Column("content_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_review_gates_content_version",
        "review_gates",
        "content_versions",
        ["content_version_id"],
        ["id"],
    )
    op.create_index(
        "ix_review_gates_content_version",
        "review_gates",
        ["content_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_gates_content_version", table_name="review_gates")
    op.drop_constraint("fk_review_gates_content_version", "review_gates", type_="foreignkey")
    op.drop_column("review_gates", "content_version_id")
