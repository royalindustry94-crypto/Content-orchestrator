"""Permit append-only Compliance and Chief Auditor reruns.

Revision ID: 0049
Revises: 0048
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0049"
down_revision: str | None = "0048"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("uq_compliance_audit_artifact_hash", "compliance_audits", type_="unique")
    op.drop_constraint("uq_chief_audit_artifact_hash", "chief_audits", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_compliance_audit_artifact_hash",
        "compliance_audits",
        ["final_artifact_id", "artifact_hash"],
    )
    op.create_unique_constraint(
        "uq_chief_audit_artifact_hash",
        "chief_audits",
        ["final_artifact_id", "artifact_hash"],
    )
