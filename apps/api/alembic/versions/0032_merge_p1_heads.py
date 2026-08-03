"""Merge parallel P1 Alembic heads (billing, FK indexes, spend precision).

Revision ID: 0032_merge_p1
Revises: 0031, 0031_fk, 0031_spend_precision
Create Date: 2026-08-03

Does not alter schema — linearizes the three independent `0031_*` revisions
created during parallel P1 execution so `alembic upgrade head` has a single tip.
"""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0032_merge_p1"
down_revision: tuple[str, str, str] | str | None = (
    "0031",
    "0031_fk",
    "0031_spend_precision",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op merge."""


def downgrade() -> None:
    """No-op merge."""
