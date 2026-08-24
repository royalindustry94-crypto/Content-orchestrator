"""Content Department V1 persistence models.

Creation, audit, and package-readiness data stays workspace-scoped and append-only
where history matters. ContentVersion remains the canonical immutable artifact.
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
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)


class ContentDepartmentRun(
    Base,
    WorkspaceScopedMixin,
    TimestampMixin,
    ActorMixin,
    VersionMixin,
):
    __tablename__ = "content_department_runs"
    __table_args__ = (
        Index("ix_content_department_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_content_department_runs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_content_department_runs_workspace_strategy",
            "workspace_id",
            "strategy_brief_id",
        ),
        Index("ix_content_department_runs_correlation", "workspace_id", "correlation_id"),
        Index("ix_content_department_runs_strategy", "strategy_brief_id"),
        Index("ix_content_department_runs_created_by", "created_by"),
        Index("ix_content_department_runs_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    provider_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    business_context_state: Mapped[str] = mapped_column(Text, nullable=False, default="incomplete")
    max_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    creative_directions_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    packages_ready: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    packages_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CreativeDirection(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "creative_directions"
    __table_args__ = (
        Index("ix_creative_directions_workspace_strategy", "workspace_id", "strategy_brief_id"),
        Index(
            "ix_creative_directions_workspace_run",
            "workspace_id",
            "content_department_run_id",
        ),
        Index("ix_creative_directions_workspace_status", "workspace_id", "status"),
        Index("ix_creative_directions_run", "content_department_run_id"),
        Index("ix_creative_directions_strategy", "strategy_brief_id"),
        Index("ix_creative_directions_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_department_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_department_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy_brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    creative_concept: Mapped[str] = mapped_column(Text, nullable=False)
    opening_pattern: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_structure: Mapped[str | None] = mapped_column(Text, nullable=True)
    tone: Mapped[str | None] = mapped_column(Text, nullable=True)
    pacing: Mapped[str | None] = mapped_column(Text, nullable=True)
    visual_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    desired_emotion: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_claims: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    prohibited_claims: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    required_assets: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    estimated_duration: Mapped[str | None] = mapped_column(Text, nullable=True)
    production_complexity: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    risk_notes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    worker_id: Mapped[str] = mapped_column(Text, nullable=False, default="creative_director")
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="creative-director-v1"
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ContentPackage(
    Base,
    WorkspaceScopedMixin,
    TimestampMixin,
    ActorMixin,
    VersionMixin,
    SoftDeleteMixin,
):
    __tablename__ = "content_packages"
    __table_args__ = (
        UniqueConstraint("workspace_id", "content_version_id", name="uq_content_package_version"),
        Index("ix_content_packages_workspace_status", "workspace_id", "status"),
        Index("ix_content_packages_workspace_item", "workspace_id", "content_item_id"),
        Index(
            "ix_content_packages_workspace_direction",
            "workspace_id",
            "creative_direction_id",
        ),
        Index("ix_content_packages_run", "content_department_run_id"),
        Index("ix_content_packages_strategy", "strategy_brief_id"),
        Index("ix_content_packages_item", "content_item_id"),
        Index("ix_content_packages_version", "content_version_id"),
        Index("ix_content_packages_prior_version", "prior_content_version_id"),
        Index("ix_content_packages_direction", "creative_direction_id"),
        Index("ix_content_packages_created_by", "created_by"),
        Index("ix_content_packages_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_department_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_department_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    creative_direction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("creative_directions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    strategy_brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    prior_content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    writer_worker_id: Mapped[str] = mapped_column(Text, nullable=False, default="writer")
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    model: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False, default="writer-v1")
    input_references: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    package_fields: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="writer_provider_not_configured"
    )
    audit_gate_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    producer_handoff_state: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    invalidated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ContentClaim(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "content_claims"
    __table_args__ = (
        Index("ix_content_claims_workspace_version", "workspace_id", "content_version_id"),
        Index("ix_content_claims_workspace_status", "workspace_id", "verification_status"),
        Index("ix_content_claims_package", "content_package_id"),
        Index("ix_content_claims_version", "content_version_id"),
        Index("ix_content_claims_created_by", "created_by"),
        Index("ix_content_claims_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(Text, nullable=False)
    source_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    supporting_evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    verification_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    risk: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    freshness: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ContentAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "content_audits"
    __table_args__ = (
        Index(
            "ix_content_audits_workspace_package_checked",
            "workspace_id",
            "content_package_id",
            "checked_at",
        ),
        Index(
            "ix_content_audits_workspace_version_type",
            "workspace_id",
            "content_version_id",
            "auditor_type",
        ),
        Index("ix_content_audits_package", "content_package_id"),
        Index("ix_content_audits_version", "content_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    auditor_type: Mapped[str] = mapped_column(Text, nullable=False)
    auditor_worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    artifact_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    requirements_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    blocked_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    checked_at: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    retry_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ContentAuditInvalidation(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "content_audit_invalidations"
    __table_args__ = (
        UniqueConstraint(
            "content_audit_id",
            "content_version_id",
            name="uq_content_audit_invalidation",
        ),
        Index(
            "ix_content_audit_invalidations_workspace_version",
            "workspace_id",
            "content_version_id",
        ),
        Index("ix_content_audit_invalidations_audit", "content_audit_id"),
        Index("ix_content_audit_invalidations_package", "content_package_id"),
        Index("ix_content_audit_invalidations_version", "content_version_id"),
        Index("ix_content_audit_invalidations_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_audits.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_dimensions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class OriginalityFingerprint(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "originality_fingerprints"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "content_version_id",
            name="uq_originality_fingerprint_version",
        ),
        Index(
            "ix_originality_fingerprints_workspace_text",
            "workspace_id",
            "text_fingerprint",
        ),
        Index(
            "ix_originality_fingerprints_workspace_hook",
            "workspace_id",
            "hook_fingerprint",
        ),
        Index(
            "ix_originality_fingerprints_workspace_structure",
            "workspace_id",
            "structure_fingerprint",
        ),
        Index("ix_originality_fingerprints_package", "content_package_id"),
        Index("ix_originality_fingerprints_version", "content_version_id"),
        Index("ix_originality_fingerprints_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_packages.id", ondelete="CASCADE"),
        nullable=False,
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    text_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    hook_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    structure_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    semantic_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    comparison_set: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    similarity_findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
