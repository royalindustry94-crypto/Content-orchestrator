from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import DeadLetterStatus, WebhookStatus


class WebhookEvent(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Inbound webhook idempotency log. UNIQUE(source, external_event_id)."""

    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("source", "external_event_id", name="uq_webhook_source_event"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String, nullable=False)
    external_event_id: Mapped[str] = mapped_column(String, nullable=False)
    # Caller-supplied dedup key, in addition to the (source, external_event_id)
    # provider-side uniqueness — covers cases where our own submitter retries.
    idempotency_key: Mapped[str | None] = mapped_column(String, nullable=True)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status: Mapped[WebhookStatus] = mapped_column(
        SAEnum(WebhookStatus, name="webhook_status", native_enum=True),
        nullable=False,
        default=WebhookStatus.RECEIVED,
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeadLetterJob(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Jobs that exhausted retries — no silent drops."""

    __tablename__ = "dead_letter_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    related_table: Mapped[str] = mapped_column(String, nullable=False)
    related_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    job_type: Mapped[str] = mapped_column(String, nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False)
    first_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_failed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[DeadLetterStatus] = mapped_column(
        SAEnum(DeadLetterStatus, name="dead_letter_status", native_enum=True),
        nullable=False,
        default=DeadLetterStatus.PENDING,
    )
