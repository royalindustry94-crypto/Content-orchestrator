"""Workspace-scoped leads CRM for the Founder Control Center."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import Date, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin


class Lead(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin):
    __tablename__ = "leads"
    __table_args__ = (
        Index("ix_leads_workspace_status", "workspace_id", "status"),
        Index("ix_leads_workspace_follow_up", "workspace_id", "follow_up_date"),
        Index("ix_leads_workspace_email", "workspace_id", "email"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    company: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="new")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_date: Mapped[date | None] = mapped_column(Date, nullable=True)
