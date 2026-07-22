from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, PipelineRunStatus, StageRunStatus


class PipelineRun(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Mutable. One full pipeline execution; holds the live cursor and status."""

    __tablename__ = "pipeline_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    # Caller-supplied dedup key; unique per workspace when present, so a
    # retried "start run" request can't create a second run.
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
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


class PipelineStageRun(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. One row per stage attempt, written once at completion."""

    __tablename__ = "pipeline_stage_runs"
    __table_args__ = (
        UniqueConstraint("pipeline_run_id", "stage", "attempt_number", name="uq_stage_run_attempt"),
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
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Provider-specific response fields (model, tokens, request id, etc.)
    # without a column per provider. Core columns stay normalized.
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
