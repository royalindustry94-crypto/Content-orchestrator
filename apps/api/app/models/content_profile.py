from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActorMixin, Base, TimestampMixin


class WorkspaceContentProfile(Base, TimestampMixin, ActorMixin):
    """Reusable content defaults for exactly one business/client workspace."""

    __tablename__ = "workspace_content_profiles"
    __table_args__ = (
        CheckConstraint(
            "service_mode IN ('own', 'client')", name="ck_content_profile_service_mode"
        ),
        CheckConstraint(
            "default_length_seconds BETWEEN 1 AND 3600",
            name="ck_content_profile_default_length",
        ),
    )

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        primary_key=True,
    )
    service_mode: Mapped[str] = mapped_column(String(16), nullable=False)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    offer: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str] = mapped_column(Text, nullable=False)
    brand_voice: Mapped[str] = mapped_column(Text, nullable=False)
    target_platform: Mapped[str] = mapped_column(String(80), nullable=False)
    content_goal: Mapped[str] = mapped_column(Text, nullable=False)
    default_length_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
