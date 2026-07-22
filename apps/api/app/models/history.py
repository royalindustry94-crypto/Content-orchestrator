from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, WorkspaceScopedMixin
from app.models.enums import ReviewDecisionValue


class ReviewDecision(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only human-review-gate decision log."""

    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id"), nullable=True
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False
    )
    decision: Mapped[ReviewDecisionValue] = mapped_column(
        SAEnum(ReviewDecisionValue, name="review_decision_value", native_enum=True), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalyticsSnapshot(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only post-publish metric time series."""

    __tablename__ = "analytics_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderUsage(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only provider usage metering (units consumed),
    distinct from spend_logs (cost in USD).
    """

    __tablename__ = "provider_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=True
    )
    pipeline_stage_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stage_runs.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(String, nullable=False)
    operation: Mapped[str | None] = mapped_column(String, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Provider-specific usage fields (model, request id, rate tier, etc.).
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
