from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, Text, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, PipelineRunStatus, StageRunStatus


class PipelineRun(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Mutable. One full pipeline execution; holds the live cursor and status."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        Index("ix_pipeline_runs_item", "content_item_id", text("created_at DESC")),
        Index(
            "ix_pipeline_runs_workspace_running",
            "workspace_id",
            "status",
            postgresql_where=text("status = 'running'::pipeline_run_status"),
        ),
        Index(
            "uq_pipeline_runs_workspace_idem",
            "workspace_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    # Caller-supplied dedup key; unique per workspace when present, so a
    # retried "start run" request can't create a second run.
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True),
        nullable=False,
        default=ContentStage.IDEA,
    )
    status: Mapped[PipelineRunStatus] = mapped_column(
        SAEnum(PipelineRunStatus, name="pipeline_run_status", native_enum=True),
        nullable=False,
        default=PipelineRunStatus.RUNNING,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Added in migration 0014 for the orchestration engine's fuller run
    # lifecycle (paused runs, workflow definitions, distributed tracing).
    pause_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    definition_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", name="fk_pipeline_runs_definition"),
        nullable=True,
    )
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)


class PipelineStageRun(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. One row per stage attempt, written once at completion."""

    __tablename__ = "pipeline_stage_runs"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "stage", "attempt_number", name="uq_stage_run_attempt"),
        Index("ix_stage_runs_run_stage", "pipeline_run_id", "stage"),
        Index("ix_stage_runs_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[StageRunStatus] = mapped_column(
        SAEnum(StageRunStatus, name="stage_run_status", native_enum=True), nullable=False
    )
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Provider-specific response fields (model, tokens, request id, etc.)
    # without a column per provider. Core columns stay normalized.
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
