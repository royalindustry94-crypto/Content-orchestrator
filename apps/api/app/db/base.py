"""Declarative base and shared mixins.

Per the project instructions, every tenant-owned table must carry a
`workspace_id`. `WorkspaceScopedMixin` is the single place that requirement
is implemented so it can't be forgotten on a new model — new tables inherit
it rather than redeclaring the column.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class WorkspaceScopedMixin:
    """Mixin for every tenant-owned table.

    workspace_id is required (nullable=False) and indexed — every query
    against a table using this mixin must filter by workspace_id at the
    repository layer. There is no default single-tenant workspace; the
    value must come from the authenticated request context.
    """

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
