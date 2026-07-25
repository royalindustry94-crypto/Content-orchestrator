"""Worker registry and heartbeat history. Reference client only — no real
generation workers connect here in this milestone.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ARRAY, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin
from app.models.enums import WorkerStatus


class WorkerRegistration(Base, TimestampMixin, VersionMixin):
    """A worker process. workspace_id is nullable — a worker may serve all
    workspaces (typical for M4's reference client) or be pinned to one.
    Deliberately NOT WorkspaceScopedMixin (that FK is NOT NULL) since a
    global worker has no single owning workspace.
    """

    __tablename__ = "worker_registry"
    __table_args__ = (
        Index(
            "ix_worker_registry_stages",
            "supported_stages",
            unique=False,
            postgresql_using="gin",
        ),
        Index(
            "ix_worker_registry_status",
            "status",
            unique=False,
            postgresql_where=text(
                "status = ANY (ARRAY['online'::worker_status, 'busy'::worker_status])"
            ),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    supported_stages: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, default=list)
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[WorkerStatus] = mapped_column(
        SAEnum(WorkerStatus, name="worker_status", native_enum=True),
        nullable=False,
        default=WorkerStatus.OFFLINE,
    )
    max_concurrency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 0-100; derived from heartbeat recency + recent success/failure ratio.
    health_score: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    registered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WorkerHeartbeat(Base):
    """Append-only heartbeat history, for health-score computation and
    diagnosing flapping workers. Not tenant-scoped (see WorkerRegistration).
    """

    __tablename__ = "worker_heartbeats"
    __table_args__ = (
        Index(
            "ix_worker_heartbeats_worker_time",
            "worker_id",
            text("heartbeat_at DESC"),
            unique=False,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worker_registry.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[WorkerStatus] = mapped_column(
        SAEnum(WorkerStatus, name="worker_status", native_enum=True), nullable=False
    )
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
