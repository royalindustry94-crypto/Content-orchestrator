"""Add missing Compliance foreign-key indexes.

Revision ID: 0050
Revises: 0049
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "ix_human_review_packages_version",
        "human_review_packages",
        ("content_version_id",),
    ),
    (
        "ix_artifact_publication_eligibility_version",
        "artifact_publication_eligibility",
        ("content_version_id",),
    ),
    (
        "ix_artifact_publication_eligibility_decision",
        "artifact_publication_eligibility",
        ("review_decision_id",),
    ),
)


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, list(columns))


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
