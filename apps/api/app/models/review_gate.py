"""Human review gate state — pause/approve/reject/timeout/escalate."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, ReviewGateStatus


class ReviewGate(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    __tablename__ = "review_gates"
    __table_args__ = (
        Index(
            "ix_review_gates_awaiting_timeout",
            "timeout_at",
            unique=False,
            postgresql_where=text("status = 'awaiting'::review_gate_status"),
        ),
        Index("ix_review_gates_run", "pipeline_run_id", unique=False),
        Index("ix_review_gates_workspace_status", "workspace_id", "status", unique=False),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True), nullable=False
    )
    status: Mapped[ReviewGateStatus] = mapped_column(
        SAEnum(ReviewGateStatus, name="review_gate_status", native_enum=True),
        nullable=False,
        default=ReviewGateStatus.AWAITING,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timeout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
    escalation_level: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
