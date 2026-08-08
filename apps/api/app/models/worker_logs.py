"""Durable worker log events for Mission Control."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, WorkspaceScopedMixin


class WorkerLog(Base, WorkspaceScopedMixin):
    __tablename__ = "worker_logs"
    __table_args__ = (
        Index("ix_worker_logs_workspace_time", "workspace_id", text("occurred_at DESC")),
        Index("ix_worker_logs_worker_time", "worker_id", text("occurred_at DESC")),
        Index(
            "ix_worker_logs_pipeline_time",
            "pipeline_run_id",
            text("occurred_at DESC"),
            postgresql_where=text("pipeline_run_id IS NOT NULL"),
        ),
        Index(
            "ix_worker_logs_assignment_time",
            "assignment_id",
            text("occurred_at DESC"),
            postgresql_where=text("assignment_id IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("worker_registry.id", ondelete="RESTRICT"),
        nullable=False,
    )
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pipeline_runs.id", ondelete="RESTRICT"),
        nullable=True,
    )
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stage_assignments.id", ondelete="RESTRICT"),
        nullable=True,
    )
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
