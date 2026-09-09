from __future__ import annotations

import uuid

from sqlalchemy import Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActorMixin, Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin


class WorkspaceContentProfile(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin
):
    """One row per workspace: business/audience/brand-voice defaults
    collected via the guided setup wizard or edited directly in Settings.
    All fields optional — a partially-filled profile is still useful as
    defaults, and nothing here implies a live AI provider is connected
    (see TD-041, tracked separately).
    """

    __tablename__ = "workspace_content_profiles"
    __table_args__ = (
        Index(
            "uq_workspace_content_profiles_workspace", "workspace_id", unique=True
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
