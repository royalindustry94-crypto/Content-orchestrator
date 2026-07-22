"""Declarative base and shared mixins.

Per the project instructions, every tenant-owned table must carry a
`workspace_id`. `WorkspaceScopedMixin` is the single place that requirement
is implemented so it can't be forgotten on a new model — new tables inherit
it rather than redeclaring the column.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """created_at + updated_at, for mutable tables."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class CreatedAtMixin:
    """created_at only, for immutable/event tables (never UPDATEd, so an
    updated_at would always equal created_at and mislead).
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )


class ActorMixin:
    """created_by / updated_by — nullable FKs to profiles. NULL means the
    system (a worker/trigger) acted, which is a real value, not a blank.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )


class CreatedByMixin:
    """created_by only — immutable tables where a human may be the author
    (e.g. a review decision) but nothing is ever updated.
    """

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )


class VersionMixin:
    """Optimistic-concurrency counter for mutable tables. The DB trigger
    set_version_and_updated_at() advances it on every UPDATE; writers guard
    with WHERE version = :expected.
    """

    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class SoftDeleteMixin:
    """deleted_at for user-facing business entities. NULL = live."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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
