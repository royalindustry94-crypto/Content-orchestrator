from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, WorkspaceScopedMixin


class WorkspaceRole(str, enum.Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"


class WorkspaceMembership(Base, TimestampMixin, WorkspaceScopedMixin):
    __tablename__ = "workspace_memberships"
    __mapper_args__ = {"confirm_deleted_rows": False}
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
        # Matches the index created by migration 0001 (formerly implied by
        # the mixin's index=True, now declared explicitly).
        Index("ix_workspace_memberships_workspace_id", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        Enum(WorkspaceRole, name="workspace_role", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
