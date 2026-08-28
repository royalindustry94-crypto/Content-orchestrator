"""Compliance and Chief Auditor V1 persistence models.

The records are workspace scoped. Evidence and audit outputs are append-only; mutable
eligibility/readiness state is versioned so no historical audit record is rewritten.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    CreatedAtMixin,
    CreatedByMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)


class PlatformPolicySource(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "platform_policy_sources"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "platform",
            "policy_category",
            "rule_version",
            name="uq_policy_source_version",
        ),
        Index("ix_policy_sources_workspace_platform", "workspace_id", "platform"),
        Index("ix_policy_sources_workspace_status", "workspace_id", "status"),
        Index("ix_policy_sources_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    policy_category: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    effective_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_verified_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rule_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="freshness_unverified")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ArtifactRightsEvidence(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "artifact_rights_evidence"
    __table_args__ = (
        Index("ix_rights_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_rights_workspace_status", "workspace_id", "rights_status"),
        Index("ix_rights_artifact", "final_artifact_id"),
        Index("ix_rights_asset", "asset_id"),
        Index("ix_rights_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    provider_or_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_or_right_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_record: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    modification_lineage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    rights_status: Mapped[str] = mapped_column(Text, nullable=False, default="unverified")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class AuditGateManifest(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "audit_gate_manifests"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "content_type",
            "manifest_version",
            name="uq_audit_gate_manifest_version",
        ),
        Index("ix_audit_gate_manifest_workspace_active", "workspace_id", "is_active"),
        Index("ix_audit_gate_manifest_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_type: Mapped[str] = mapped_column(Text, nullable=False)
    manifest_version: Mapped[int] = mapped_column(Integer, nullable=False)
    required_gates: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ComplianceAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "compliance_audits"
    __table_args__ = (
        Index(
            "ix_compliance_audits_workspace_artifact",
            "workspace_id",
            "final_artifact_id",
        ),
        Index("ix_compliance_audits_workspace_status", "workspace_id", "status"),
        Index("ix_compliance_audits_artifact", "final_artifact_id"),
        Index("ix_compliance_audits_version", "content_version_id"),
        Index("ix_compliance_audits_policy", "policy_source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_platform: Mapped[str] = mapped_column(Text, nullable=False)
    policy_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("platform_policy_sources.id", ondelete="SET NULL"),
        nullable=True,
    )
    policy_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    compliance_worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    input_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_disclosures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rights_status: Mapped[str] = mapped_column(Text, nullable=False, default="unverified")
    reused_content_risk: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    monetization_risk: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verification_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    retry_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ComplianceInvalidation(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "compliance_invalidations"
    __table_args__ = (
        UniqueConstraint("compliance_audit_id", "reason", name="uq_compliance_invalidation_reason"),
        Index(
            "ix_compliance_invalidations_workspace_artifact",
            "workspace_id",
            "final_artifact_id",
        ),
        Index("ix_compliance_invalidations_audit", "compliance_audit_id"),
        Index("ix_compliance_invalidations_artifact", "final_artifact_id"),
        Index("ix_compliance_invalidations_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    compliance_audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("compliance_audits.id", ondelete="CASCADE"),
        nullable=False,
    )
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_dimensions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class ChiefAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "chief_audits"
    __table_args__ = (
        Index("ix_chief_audits_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_chief_audits_workspace_status", "workspace_id", "status"),
        Index("ix_chief_audits_artifact", "final_artifact_id"),
        Index("ix_chief_audits_version", "content_version_id"),
        Index("ix_chief_audits_manifest", "gate_manifest_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    gate_manifest_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audit_gate_manifests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chief_auditor_worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    gate_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    lineage_status: Mapped[str] = mapped_column(Text, nullable=False, default="incomplete")
    version_integrity_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="incomplete"
    )
    cost_reconciliation_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="incomplete"
    )
    provider_reconciliation_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="incomplete"
    )
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    blockers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    retry_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ChiefAuditInvalidation(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "chief_audit_invalidations"
    __table_args__ = (
        UniqueConstraint("chief_audit_id", "reason", name="uq_chief_audit_invalidation_reason"),
        Index(
            "ix_chief_audit_invalidations_workspace_artifact",
            "workspace_id",
            "final_artifact_id",
        ),
        Index("ix_chief_audit_invalidations_chief", "chief_audit_id"),
        Index("ix_chief_audit_invalidations_artifact", "final_artifact_id"),
        Index("ix_chief_audit_invalidations_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chief_audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chief_audits.id", ondelete="CASCADE"),
        nullable=False,
    )
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_dimensions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class HumanReviewPackage(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "human_review_packages"
    __table_args__ = (
        UniqueConstraint(
            "final_artifact_id",
            "artifact_hash",
            name="uq_human_review_package_artifact_hash",
        ),
        Index(
            "ix_human_review_packages_workspace_artifact",
            "workspace_id",
            "final_artifact_id",
        ),
        Index("ix_human_review_packages_workspace_gate", "workspace_id", "review_gate_id"),
        Index("ix_human_review_packages_artifact", "final_artifact_id"),
        Index("ix_human_review_packages_version", "content_version_id"),
        Index("ix_human_review_packages_chief", "chief_audit_id"),
        Index("ix_human_review_packages_gate", "review_gate_id"),
        Index("ix_human_review_packages_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    chief_audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chief_audits.id", ondelete="RESTRICT"),
        nullable=False,
    )
    review_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_gates.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_platform: Mapped[str] = mapped_column(Text, nullable=False)
    package_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_disclosures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ArtifactPublicationEligibility(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin
):
    __tablename__ = "artifact_publication_eligibility"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "final_artifact_id",
            "target_platform",
            name="uq_artifact_publication_eligibility",
        ),
        Index(
            "ix_artifact_publication_eligibility_workspace_artifact",
            "workspace_id",
            "final_artifact_id",
        ),
        Index(
            "ix_artifact_publication_eligibility_workspace_status",
            "workspace_id",
            "status",
        ),
        Index("ix_artifact_publication_eligibility_artifact", "final_artifact_id"),
        Index("ix_artifact_publication_eligibility_version", "content_version_id"),
        Index("ix_artifact_publication_eligibility_chief", "chief_audit_id"),
        Index("ix_artifact_publication_eligibility_gate", "review_gate_id"),
        Index("ix_artifact_publication_eligibility_decision", "review_decision_id"),
        Index("ix_artifact_publication_eligibility_created_by", "created_by"),
        Index("ix_artifact_publication_eligibility_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("final_artifacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_platform: Mapped[str] = mapped_column(Text, nullable=False)
    chief_audit_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chief_audits.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_gates.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_decision_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("review_decisions.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    blocking_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    publication_eligible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
