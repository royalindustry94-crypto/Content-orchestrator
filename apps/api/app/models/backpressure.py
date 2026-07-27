"""workspace_backpressure_state and provider_concurrency_budgets (WS4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin
from app.models.enums import BackpressureState


class WorkspaceBackpressureState(Base, VersionMixin):
    """One row per workspace tracking observed queue-depth pressure.

    Writes are service-role only; members may SELECT (FORCE RLS).
    """

    __tablename__ = "workspace_backpressure_state"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[BackpressureState] = mapped_column(
        SAEnum(
            BackpressureState,
            name="backpressure_state",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=BackpressureState.NORMAL,
    )
    pending_depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    entered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProviderConcurrencyBudget(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    """Per-workspace per-provider in-flight concurrency ceiling (WS4)."""

    __tablename__ = "provider_concurrency_budgets"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "provider", name="uq_provider_concurrency_budgets_ws_provider"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    max_concurrent: Mapped[int] = mapped_column(Integer, nullable=False)
