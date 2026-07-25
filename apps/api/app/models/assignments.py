"""stage_assignments: the binding between a runnable stage and a worker,
including the lease that makes crash recovery uniform.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, StageAssignmentStatus


class StageAssignment(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    __tablename__ = "stage_assignments"
    __table_args__ = (
        Index(
            "ix_stage_assignments_lease",
            "lease_expires_at",
            unique=False,
            postgresql_where=text(
                "status = ANY (ARRAY['dispatched'::stage_assignment_status, "
                "'acknowledged'::stage_assignment_status])"
            ),
        ),
        Index(
            "ix_stage_assignments_pending_stage",
            "stage",
            "created_at",
            unique=False,
            postgresql_where=text("status = 'pending'::stage_assignment_status"),
        ),
        Index("ix_stage_assignments_run", "pipeline_run_id", unique=False),
        Index(
            "ix_stage_assignments_worker",
            "worker_id",
            unique=False,
            postgresql_where=text("worker_id IS NOT NULL"),
        ),
        Index(
            "uq_stage_assignments_workspace_idem",
            "workspace_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=False
    )
    stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worker_registry.id"), nullable=True
    )
    status: Mapped[StageAssignmentStatus] = mapped_column(
        SAEnum(StageAssignmentStatus, name="stage_assignment_status", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=StageAssignmentStatus.PENDING,
    )
    # Dedup key so a re-dispatch of the same (run, stage, attempt) can't
    # create two assignments; unique per workspace when present.
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Tracing (amendment 1): carried onto every assignment.
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
