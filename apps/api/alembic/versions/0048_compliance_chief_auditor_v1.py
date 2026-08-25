"""Create bounded Compliance and Chief Auditor V1 records.

Revision ID: 0048
Revises: 0047
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_delete_trigger,
    attach_immutable_trigger,
    attach_version_trigger,
    enable_rls,
    grant_runtime,
    policy_insert_roles,
    policy_select_members,
    policy_update_roles,
)

revision: str = "0048"
down_revision: str | None = "0047"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def _workspace() -> sa.Column:
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def _created() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
    ]


def _actor() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    ]


def _json(default: str) -> sa.Column:
    return sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text(default),
    )


def _indexes(table: str, pairs: tuple[tuple[str, list[str]], ...]) -> None:
    for name, columns in pairs:
        op.create_index(name, table, columns, unique=False)


def upgrade() -> None:
    op.create_table(
        "platform_policy_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("policy_category", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rule_version", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="freshness_unverified"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created(),
        sa.UniqueConstraint(
            "workspace_id",
            "platform",
            "policy_category",
            "rule_version",
            name="uq_policy_source_version",
        ),
    )
    _indexes(
        "platform_policy_sources",
        (
            ("ix_policy_sources_workspace_platform", ["workspace_id", "platform"]),
            ("ix_policy_sources_workspace_status", ["workspace_id", "status"]),
            ("ix_policy_sources_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "audit_gate_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("manifest_version", sa.Integer(), nullable=False),
        sa.Column(
            "required_gates",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created(),
        sa.UniqueConstraint(
            "workspace_id",
            "content_type",
            "manifest_version",
            name="uq_audit_gate_manifest_version",
        ),
    )
    _indexes(
        "audit_gate_manifests",
        (
            ("ix_audit_gate_manifest_workspace_active", ["workspace_id", "is_active"]),
            ("ix_audit_gate_manifest_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "artifact_rights_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("provider_or_source", sa.Text(), nullable=True),
        sa.Column("license_or_right_basis", sa.Text(), nullable=True),
        sa.Column(
            "generation_record",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source_reference", sa.Text(), nullable=True),
        sa.Column(
            "modification_lineage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("rights_status", sa.Text(), nullable=False, server_default="unverified"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created(),
    )
    _indexes(
        "artifact_rights_evidence",
        (
            ("ix_rights_workspace_artifact", ["workspace_id", "final_artifact_id"]),
            ("ix_rights_workspace_status", ["workspace_id", "rights_status"]),
            ("ix_rights_artifact", ["final_artifact_id"]),
            ("ix_rights_asset", ["asset_id"]),
            ("ix_rights_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "compliance_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_platform", sa.Text(), nullable=False),
        sa.Column(
            "policy_source_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_policy_sources.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("policy_version", sa.Text(), nullable=True),
        sa.Column("compliance_worker_id", sa.Text(), nullable=False),
        sa.Column(
            "input_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("risk_level", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_disclosures",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("rights_status", sa.Text(), nullable=False, server_default="unverified"),
        sa.Column("reused_content_risk", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("monetization_risk", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("provider_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("verification_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column(
            "retry_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "final_artifact_id",
            "artifact_hash",
            name="uq_compliance_audit_artifact_hash",
        ),
    )
    _indexes(
        "compliance_audits",
        (
            (
                "ix_compliance_audits_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            ("ix_compliance_audits_workspace_status", ["workspace_id", "status"]),
            ("ix_compliance_audits_artifact", ["final_artifact_id"]),
            ("ix_compliance_audits_version", ["content_version_id"]),
            ("ix_compliance_audits_policy", ["policy_source_id"]),
        ),
    )

    op.create_table(
        "compliance_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "compliance_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compliance_audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "affected_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        *_created(),
        sa.UniqueConstraint(
            "compliance_audit_id", "reason", name="uq_compliance_invalidation_reason"
        ),
    )
    _indexes(
        "compliance_invalidations",
        (
            (
                "ix_compliance_invalidations_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            ("ix_compliance_invalidations_audit", ["compliance_audit_id"]),
            ("ix_compliance_invalidations_artifact", ["final_artifact_id"]),
            ("ix_compliance_invalidations_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "chief_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "gate_manifest_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("audit_gate_manifests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("chief_auditor_worker_id", sa.Text(), nullable=False),
        sa.Column(
            "gate_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("lineage_status", sa.Text(), nullable=False, server_default="incomplete"),
        sa.Column(
            "version_integrity_status",
            sa.Text(),
            nullable=False,
            server_default="incomplete",
        ),
        sa.Column(
            "cost_reconciliation_status",
            sa.Text(),
            nullable=False,
            server_default="incomplete",
        ),
        sa.Column(
            "provider_reconciliation_status",
            sa.Text(),
            nullable=False,
            server_default="incomplete",
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blockers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column(
            "retry_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "final_artifact_id", "artifact_hash", name="uq_chief_audit_artifact_hash"
        ),
    )
    _indexes(
        "chief_audits",
        (
            (
                "ix_chief_audits_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            ("ix_chief_audits_workspace_status", ["workspace_id", "status"]),
            ("ix_chief_audits_artifact", ["final_artifact_id"]),
            ("ix_chief_audits_version", ["content_version_id"]),
            ("ix_chief_audits_manifest", ["gate_manifest_id"]),
        ),
    )

    op.create_table(
        "chief_audit_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "chief_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chief_audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "affected_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        *_created(),
        sa.UniqueConstraint("chief_audit_id", "reason", name="uq_chief_audit_invalidation_reason"),
    )
    _indexes(
        "chief_audit_invalidations",
        (
            (
                "ix_chief_audit_invalidations_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            ("ix_chief_audit_invalidations_chief", ["chief_audit_id"]),
            ("ix_chief_audit_invalidations_artifact", ["final_artifact_id"]),
            ("ix_chief_audit_invalidations_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "human_review_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "chief_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chief_audits.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "review_gate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_gates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("target_platform", sa.Text(), nullable=False),
        sa.Column(
            "package_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_disclosures",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created(),
        sa.UniqueConstraint(
            "final_artifact_id",
            "artifact_hash",
            name="uq_human_review_package_artifact_hash",
        ),
    )
    _indexes(
        "human_review_packages",
        (
            (
                "ix_human_review_packages_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            (
                "ix_human_review_packages_workspace_gate",
                ["workspace_id", "review_gate_id"],
            ),
            ("ix_human_review_packages_artifact", ["final_artifact_id"]),
            ("ix_human_review_packages_chief", ["chief_audit_id"]),
            ("ix_human_review_packages_gate", ["review_gate_id"]),
            ("ix_human_review_packages_created_by", ["created_by"]),
        ),
    )

    op.create_table(
        "artifact_publication_eligibility",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_platform", sa.Text(), nullable=False),
        sa.Column(
            "chief_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chief_audits.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "review_gate_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_gates.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "review_decision_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("review_decisions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column(
            "blocking_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "publication_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor(),
        sa.UniqueConstraint(
            "workspace_id",
            "final_artifact_id",
            "target_platform",
            name="uq_artifact_publication_eligibility",
        ),
    )
    _indexes(
        "artifact_publication_eligibility",
        (
            (
                "ix_artifact_publication_eligibility_workspace_artifact",
                ["workspace_id", "final_artifact_id"],
            ),
            (
                "ix_artifact_publication_eligibility_workspace_status",
                ["workspace_id", "status"],
            ),
            ("ix_artifact_publication_eligibility_artifact", ["final_artifact_id"]),
            ("ix_artifact_publication_eligibility_chief", ["chief_audit_id"]),
            ("ix_artifact_publication_eligibility_gate", ["review_gate_id"]),
            ("ix_artifact_publication_eligibility_created_by", ["created_by"]),
            ("ix_artifact_publication_eligibility_updated_by", ["updated_by"]),
        ),
    )

    immutable = (
        "platform_policy_sources",
        "artifact_rights_evidence",
        "audit_gate_manifests",
        "compliance_audits",
        "compliance_invalidations",
        "chief_audits",
        "chief_audit_invalidations",
        "human_review_packages",
    )
    for table in immutable:
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)
        enable_rls(table)
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)
    attach_version_trigger("artifact_publication_eligibility")
    enable_rls("artifact_publication_eligibility")
    grant_runtime("artifact_publication_eligibility")
    policy_select_members("artifact_publication_eligibility", _ALL)
    policy_insert_roles("artifact_publication_eligibility", _EDIT)
    policy_update_roles("artifact_publication_eligibility", _EDIT)


def downgrade() -> None:
    immutable = (
        "human_review_packages",
        "chief_audit_invalidations",
        "chief_audits",
        "compliance_invalidations",
        "compliance_audits",
        "artifact_rights_evidence",
        "audit_gate_manifests",
        "platform_policy_sources",
    )
    for table in immutable:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete ON {table};")
    table = "artifact_publication_eligibility"
    op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
    op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
    op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
    op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
    op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
    op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_version ON {table};")
    for table in (
        "artifact_publication_eligibility",
        "human_review_packages",
        "chief_audit_invalidations",
        "chief_audits",
        "compliance_invalidations",
        "compliance_audits",
        "artifact_rights_evidence",
        "audit_gate_manifests",
        "platform_policy_sources",
    ):
        op.drop_table(table)
