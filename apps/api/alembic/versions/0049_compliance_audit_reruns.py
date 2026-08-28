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

_AUDIT_TABLES = ("compliance_audits", "chief_audits")


def upgrade() -> None:
    op.drop_constraint("uq_compliance_audit_artifact_hash", "compliance_audits", type_="unique")
    op.drop_constraint("uq_chief_audit_artifact_hash", "chief_audits", type_="unique")


def _rerun_mapping_sql(table_name: str) -> str:
    """Return a deterministic mapping from each duplicate rerun to its canonical audit.

    Revision 0048 allowed one audit per exact artifact hash. Revision 0049 removes
    that constraint to support immutable append-only reruns. A downgrade must first
    fold reruns back into the earliest audit to satisfy the predecessor's schema;
    downstream foreign keys are repointed before duplicate rows are removed.
    """
    return f"""
        WITH ranked AS (
            SELECT
                id,
                first_value(id) OVER (
                    PARTITION BY final_artifact_id, artifact_hash
                    ORDER BY created_at ASC, id ASC
                ) AS canonical_id,
                row_number() OVER (
                    PARTITION BY final_artifact_id, artifact_hash
                    ORDER BY created_at ASC, id ASC
                ) AS row_number
            FROM {table_name}
        )
        SELECT id, canonical_id
        FROM ranked
        WHERE row_number > 1
    """


def _drop_immutable_triggers() -> None:
    """Temporarily allow downgrade-only canonicalization inside Alembic's transaction."""
    for table_name in _AUDIT_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable ON {table_name};")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table_name}_immutable_delete ON {table_name};")


def _restore_immutable_triggers() -> None:
    """Restore the exact 0048 append-only guards before the downgrade commits."""
    for table_name in _AUDIT_TABLES:
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_immutable BEFORE UPDATE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_update();"
        )
        op.execute(
            f"CREATE TRIGGER trg_{table_name}_immutable_delete BEFORE DELETE ON {table_name} "
            "FOR EACH ROW EXECUTE FUNCTION prevent_delete();"
        )


def downgrade() -> None:
    # Preserve dependent records while intentionally collapsing the rerun-only
    # rows that cannot exist in the 0048 unique-constraint schema. The trigger
    # change is migration-transaction-local; 0048 guards are restored below.
    _drop_immutable_triggers()

    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("compliance_audits")})
        UPDATE compliance_invalidations AS invalidation
        SET compliance_audit_id = reruns.canonical_id
        FROM reruns
        WHERE invalidation.compliance_audit_id = reruns.id
        """
    )
    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("compliance_audits")})
        DELETE FROM compliance_audits AS audit
        USING reruns
        WHERE audit.id = reruns.id
        """
    )

    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("chief_audits")})
        UPDATE chief_audit_invalidations AS invalidation
        SET chief_audit_id = reruns.canonical_id
        FROM reruns
        WHERE invalidation.chief_audit_id = reruns.id
        """
    )
    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("chief_audits")})
        UPDATE human_review_packages AS package
        SET chief_audit_id = reruns.canonical_id
        FROM reruns
        WHERE package.chief_audit_id = reruns.id
        """
    )
    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("chief_audits")})
        UPDATE artifact_publication_eligibility AS eligibility
        SET chief_audit_id = reruns.canonical_id
        FROM reruns
        WHERE eligibility.chief_audit_id = reruns.id
        """
    )
    op.execute(
        f"""
        WITH reruns AS ({_rerun_mapping_sql("chief_audits")})
        DELETE FROM chief_audits AS audit
        USING reruns
        WHERE audit.id = reruns.id
        """
    )

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
    _restore_immutable_triggers()
