"""The transactional outbox: outbox_events plus consumer bookkeeping.

Amendment (distributed tracing): trace_id/span_id are carried on every
event alongside correlation_id/causation_id, so a tracing backend can be
attached later without an envelope redesign.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import OutboxEventStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class OutboxEvent(Base, WorkspaceScopedMixin, VersionMixin):
    """Append-only event log — the bus. Status/delivery_attempts are the
    only fields ever mutated post-insert (by the relay), so this carries a
    version column rather than the prevent_update trigger used for pure
    history tables.
    """

    __tablename__ = "outbox_events"
    __table_args__ = (
        Index(
            "uq_outbox_events_aggregate_sequence",
            "aggregate_type",
            "aggregate_id",
            "sequence",
            unique=True,
        ),
        Index("ix_outbox_events_correlation", "correlation_id", unique=False),
        Index(
            "ix_outbox_events_status_time",
            "status",
            "occurred_at",
            unique=False,
            postgresql_where=text("status = 'pending'::outbox_event_status"),
        ),
        Index("ix_outbox_events_workspace", "workspace_id", unique=False),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    aggregate_type: Mapped[str] = mapped_column(Text, nullable=False)
    aggregate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    causation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Distributed tracing (amendment): propagated end-to-end so every
    # log/metric/audit line can join back to a single execution trace.
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    span_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxEventStatus] = mapped_column(
        SAEnum(OutboxEventStatus, name="outbox_event_status", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=OutboxEventStatus.PENDING,
    )
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    produced_by: Mapped[str] = mapped_column(Text, nullable=False)
    # set_version_and_updated_at() (the same trigger every other mutable
    # M4 table uses) stamps this on every UPDATE (status/delivery_attempts
    # changes made by the relay). Mapped explicitly here rather than via
    # TimestampMixin, since OutboxEvent's business timestamp is
    # occurred_at, not created_at.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class EventConsumer(Base, TimestampMixin, VersionMixin):
    """Registry of logical consumers. Not workspace-scoped — a consumer is
    a process-level concept (e.g. "pipeline-controller"), spanning tenants.
    """

    __tablename__ = "event_consumers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    max_event_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    max_delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=10)


class ConsumerCheckpoint(Base, TimestampMixin, VersionMixin):
    """Per-(consumer, aggregate partition) high-water mark. Advancing this
    only after the handler's effects commit is what makes redelivery safe.
    """

    __tablename__ = "consumer_checkpoints"
    __table_args__ = (
        UniqueConstraint(
            "consumer_id", "aggregate_type", "partition_key", name="uq_consumer_checkpoint"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    consumer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("event_consumers.id", ondelete="CASCADE"), nullable=False
    )
    aggregate_type: Mapped[str] = mapped_column(Text, nullable=False)
    partition_key: Mapped[str] = mapped_column(Text, nullable=False)
    last_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
