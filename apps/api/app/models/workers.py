"""Worker registry and heartbeat history. Reference client only — no real
generation workers connect here in this milestone.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import ARRAY as PGARRAY
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin
from app.models.enums import WorkerCredentialStatus, WorkerStatus


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
    supported_stages: Mapped[list[str]] = mapped_column(PGARRAY(Text), nullable=False, default=list)
    capabilities: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[WorkerStatus] = mapped_column(
        SAEnum(
            WorkerStatus,
            name="worker_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
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
    # WS1 identity/lifecycle columns (migration 0025).
    instance_key: Mapped[str] = mapped_column(
        Text, nullable=False, default=lambda: str(uuid.uuid4())
    )
    worker_version: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Admin *intent* to decommission — deliberately separate from `status`,
    # which is an observation reported by the worker/liveness sweep.
    drain: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Soft deregistration: rows are never hard-deleted (heartbeat history
    # and audit trails keep valid FKs). Re-registration revives the row.
    deregistered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WorkerCredential(Base):
    """Per-worker machine credential (WS1 design amendment 1). The secret
    is stored only as a SHA-256 hash of a high-entropy random token —
    never plaintext. Multiple ACTIVE credentials per worker are legal so
    rotation is zero-downtime (old credential keeps a grace `expires_at`
    while the new one is already in use). Service-role-only table: FORCE
    RLS with no policies and no user-role grants.
    """

    __tablename__ = "worker_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worker_registry.id", ondelete="CASCADE"), nullable=False
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    secret_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[WorkerCredentialStatus] = mapped_column(
        SAEnum(
            WorkerCredentialStatus,
            name="worker_credential_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=WorkerCredentialStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


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
        SAEnum(
            WorkerStatus,
            name="worker_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    current_load: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
