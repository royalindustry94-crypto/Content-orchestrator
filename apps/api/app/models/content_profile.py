from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import Index, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ActorMixin, Base, TimestampMixin, VersionMixin, WorkspaceScopedMixin


class WorkspaceContentProfile(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    """One row per workspace: business/audience/brand-voice defaults
    collected via the guided setup wizard or edited directly in Settings.
    All fields optional — a partially-filled profile is still useful as
    defaults, and nothing here implies a live AI provider is connected
    (see TD-041, tracked separately).
    """

    __tablename__ = "workspace_content_profiles"
    __table_args__ = (
        Index("uq_workspace_content_profiles_workspace", "workspace_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand_voice: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_goal: Mapped[str | None] = mapped_column(Text, nullable=True)


class _ContentProfileFields(Protocol):
    """Structural shape shared by `WorkspaceContentProfile` (the ORM row)
    and `ContentProfileOut` (the API schema) — this function is called with
    either, and only ever reads these six fields, so it's typed against the
    shape rather than importing the schema here (which would invert the
    usual schemas-import-models dependency direction).
    """

    business_name: str | None
    offer: str | None
    target_audience: str | None
    brand_voice: str | None
    target_platform: str | None
    content_goal: str | None


def is_content_profile_complete(profile: _ContentProfileFields | None) -> bool:
    """True once every field a first-time-setup wizard collects has a
    value. Shared by the API output schema (`ContentProfileOut.is_complete`)
    and by generation-defaults callers (Strategy/Content Department manual
    runs) that need to know, truthfully, whether a workspace's saved
    business context is actually usable as a default — not a
    backend-enforced gate on anything by itself.
    """
    if profile is None:
        return False
    return all(
        [
            profile.business_name,
            profile.offer,
            profile.target_audience,
            profile.brand_voice,
            profile.target_platform,
            profile.content_goal,
        ]
    )


async def get_business_context_state(session: AsyncSession, *, workspace_id: uuid.UUID) -> str:
    """Returns "complete" or "incomplete" — the truthful state of the workspace's
    saved `WorkspaceContentProfile`, for services (Strategy, Content
    Department) that report `business_context_state` on their runs and
    summaries. A missing profile is honestly "incomplete", not an error.
    """
    profile = (
        await session.execute(
            select(WorkspaceContentProfile).where(
                WorkspaceContentProfile.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    return "complete" if is_content_profile_complete(profile) else "incomplete"
