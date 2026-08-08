"""Workspace Stripe billing / entitlement state."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, false, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin


def _utcnow() -> datetime:
    return datetime.now(UTC)


class WorkspaceBilling(Base, TimestampMixin, VersionMixin):
    """One billing row per workspace — Stripe customer + subscription mirror."""

    __tablename__ = "workspace_billing"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    plan: Mapped[str] = mapped_column(Text, nullable=False, default="none")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="inactive")
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )


class BillingWebhookEvent(Base):
    """Idempotent Stripe webhook receipt log (owner-connection only)."""

    __tablename__ = "billing_webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    stripe_event_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True
    )
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
