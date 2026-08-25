"""Producer and Media QA V1 persistence models.

Production is bounded and workspace-scoped. Generated components, final artifacts,
Media QA evidence, repairs, and invalidations are append-only where lineage matters.
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


class ProductionJob(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "production_jobs"
    __table_args__ = (
        Index("ix_production_jobs_workspace_created", "workspace_id", "created_at"),
        Index("ix_production_jobs_workspace_status", "workspace_id", "status"),
        Index("ix_production_jobs_workspace_package", "workspace_id", "content_package_id"),
        Index("ix_production_jobs_workspace_version", "workspace_id", "content_version_id"),
        Index("ix_production_jobs_package", "content_package_id"),
        Index("ix_production_jobs_item", "content_item_id"),
        Index("ix_production_jobs_version", "content_version_id"),
        Index("ix_production_jobs_pipeline", "pipeline_run_id"),
        Index("ix_production_jobs_created_by", "created_by"),
        Index("ix_production_jobs_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_package_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_packages.id", ondelete="RESTRICT"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="SET NULL"), nullable=True
    )
    producer_worker_id: Mapped[str] = mapped_column(Text, nullable=False, default="producer")
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_assets: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    provider_plan: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    provider_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    max_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_render_calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    max_total_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_repair_cycles: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    deadline_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    render_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repair_cycles_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    actual_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProductionAsset(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "production_assets"
    __table_args__ = (
        UniqueConstraint("workspace_id", "asset_id", name="uq_production_asset_asset"),
        Index("ix_production_assets_workspace_job", "workspace_id", "production_job_id"),
        Index("ix_production_assets_workspace_version", "workspace_id", "content_version_id"),
        Index("ix_production_assets_job", "production_job_id"),
        Index("ix_production_assets_asset", "asset_id"),
        Index("ix_production_assets_version", "content_version_id"),
        Index("ix_production_assets_item", "content_item_id"),
        Index("ix_production_assets_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="RESTRICT"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    asset_type: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    provider_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_inputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    generation_settings: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    model_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    dimensions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class FinalArtifact(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "final_artifacts"
    __table_args__ = (
        UniqueConstraint("workspace_id", "artifact_hash", name="uq_final_artifact_hash"),
        Index("ix_final_artifacts_workspace_job", "workspace_id", "production_job_id"),
        Index("ix_final_artifacts_workspace_version", "workspace_id", "content_version_id"),
        Index("ix_final_artifacts_job", "production_job_id"),
        Index("ix_final_artifacts_version", "content_version_id"),
        Index("ix_final_artifacts_item", "content_item_id"),
        Index("ix_final_artifacts_render_asset", "render_asset_id"),
        Index("ix_final_artifacts_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    render_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="SET NULL"), nullable=True
    )
    render_provider: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    render_job_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    storage_reference: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    duration_seconds: Mapped[float | None] = mapped_column(Numeric(12, 3), nullable=True)
    resolution: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    aspect_ratio: Mapped[str | None] = mapped_column(Text, nullable=True)
    container: Mapped[str | None] = mapped_column(Text, nullable=True)
    codec: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MediaQaResult(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "media_qa_results"
    __table_args__ = (
        UniqueConstraint("final_artifact_id", "artifact_hash", name="uq_media_qa_artifact_hash"),
        Index("ix_media_qa_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_media_qa_workspace_status", "workspace_id", "status"),
        Index("ix_media_qa_artifact", "final_artifact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("final_artifacts.id", ondelete="CASCADE"), nullable=False
    )
    artifact_hash: Mapped[str] = mapped_column(Text, nullable=False)
    auditor_worker_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    checks_run: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    visual_findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    audio_findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    subtitle_findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    script_alignment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    platform_check: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    package_alignment: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evidence: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recommended_repair: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ProductionRepair(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "production_repairs"
    __table_args__ = (
        Index("ix_production_repairs_workspace_job", "workspace_id", "production_job_id"),
        Index("ix_production_repairs_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_production_repairs_job", "production_job_id"),
        Index("ix_production_repairs_artifact", "final_artifact_id"),
        Index("ix_production_repairs_qa", "media_qa_result_id"),
        Index("ix_production_repairs_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    production_job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("production_jobs.id", ondelete="RESTRICT"), nullable=False
    )
    final_artifact_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("final_artifacts.id", ondelete="SET NULL"), nullable=True
    )
    media_qa_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_qa_results.id", ondelete="SET NULL"), nullable=True
    )
    affected_component: Mapped[str] = mapped_column(Text, nullable=False)
    finding_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    repair_operation: Mapped[str] = mapped_column(Text, nullable=False)
    repair_cycle: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_references: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ArtifactInvalidation(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "artifact_invalidations"
    __table_args__ = (
        UniqueConstraint("final_artifact_id", "reason", name="uq_artifact_invalidation_reason"),
        Index("ix_artifact_invalidations_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_artifact_invalidations_qa", "media_qa_result_id"),
        Index("ix_artifact_invalidations_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("final_artifacts.id", ondelete="CASCADE"), nullable=False
    )
    media_qa_result_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("media_qa_results.id", ondelete="SET NULL"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    affected_dimensions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)


class ProductionReadiness(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "production_readiness"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "final_artifact_id", name="uq_production_readiness_artifact"
        ),
        Index("ix_production_readiness_workspace_artifact", "workspace_id", "final_artifact_id"),
        Index("ix_production_readiness_workspace_status", "workspace_id", "status"),
        Index("ix_production_readiness_artifact", "final_artifact_id"),
        Index("ix_production_readiness_version", "content_version_id"),
        Index("ix_production_readiness_created_by", "created_by"),
        Index("ix_production_readiness_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    final_artifact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("final_artifacts.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id", ondelete="RESTRICT"), nullable=False
    )
    media_qa_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    compliance_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    chief_audit_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    human_review_state: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    blocking_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    total_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
