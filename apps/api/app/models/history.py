from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, WorkspaceScopedMixin
from app.models.enums import ReviewDecisionValue


class ReviewDecision(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only human-review-gate decision log."""

    __tablename__ = "review_decisions"
    __table_args__ = (
        Index("ix_review_decisions_item", "content_item_id", text("created_at DESC")),
        Index("ix_review_decisions_workspace", "workspace_id"),
    )

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
        SAEnum(ReviewDecisionValue, name="review_decision_value", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AnalyticsSnapshot(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only post-publish metric time series."""

    __tablename__ = "analytics_snapshots"
    __table_args__ = (
        Index(
            "ix_analytics_item_metric_time",
            "content_item_id",
            "metric",
            text("captured_at DESC"),
        ),
        Index("ix_analytics_workspace_time", "workspace_id", text("captured_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderUsage(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """Immutable. Append-only provider usage metering (units consumed),
    distinct from spend_logs (cost in USD).
    """

    __tablename__ = "provider_usage"
    __table_args__ = (
        Index(
            "ix_provider_usage_item",
            "content_item_id",
            postgresql_where=text("content_item_id IS NOT NULL"),
        ),
        Index(
            "ix_provider_usage_workspace_provider_time",
            "workspace_id",
            "provider",
            text("occurred_at DESC"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id"), nullable=True
    )
    pipeline_stage_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stage_runs.id"), nullable=True
    )
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    operation: Mapped[str | None] = mapped_column(Text, nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric, nullable=False)
    unit_type: Mapped[str] = mapped_column(Text, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Provider-specific usage fields (model, request id, rate tier, etc.).
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
