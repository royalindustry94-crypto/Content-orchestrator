"""Add missing Producer foreign-key indexes.

Revision ID: 0047
Revises: 0046
Create Date: 2026-08-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_production_assets_item",
        "production_assets",
        ["content_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_final_artifacts_item",
        "final_artifacts",
        ["content_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_final_artifacts_render_asset",
        "final_artifacts",
        ["render_asset_id"],
        unique=False,
    )
    op.create_index(
        "ix_production_readiness_version",
        "production_readiness",
        ["content_version_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_production_readiness_version", table_name="production_readiness")
    op.drop_index("ix_final_artifacts_render_asset", table_name="final_artifacts")
    op.drop_index("ix_final_artifacts_item", table_name="final_artifacts")
    op.drop_index("ix_production_assets_item", table_name="production_assets")
