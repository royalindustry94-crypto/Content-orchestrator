from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, ReservationStatus


class SpendLog(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable ledger — source of truth for actual spend."""

    __tablename__ = "spend_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[ContentStage | None] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True), nullable=True
    )
    units: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Provider-specific billing detail without a column per provider.
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class SpendReservation(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Mutable. Reserve estimated cost before a job stage starts; commit or
    release when it finishes. Cap checks sum spend_logs + open reservations.
    """

    __tablename__ = "spend_reservations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Added in migration 0020 for the orchestration engine — without this,
    # releasing "this run's" reservations on failure/cancel has no correct
    # scope (content_item_id alone doesn't distinguish between retried runs
    # of the same item).
    pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id", ondelete="CASCADE"), nullable=True
    )
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    stage: Mapped[ContentStage | None] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True), nullable=True
    )
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    status: Mapped[ReservationStatus] = mapped_column(
        SAEnum(ReservationStatus, name="reservation_status", native_enum=True),
        nullable=False,
        default=ReservationStatus.RESERVED,
    )
