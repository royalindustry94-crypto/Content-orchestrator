from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Numeric, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)
from app.models.enums import ProviderCredentialStatus


class ContentPillar(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
):
    __tablename__ = "content_pillars"
    __table_args__ = (
        Index("ix_content_pillars_workspace", "workspace_id"),
        Index(
            "uq_content_pillars_workspace_name",
            "workspace_id",
            "name",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)


class SpendCap(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "spend_caps"
    __table_args__ = (
        Index(
            "uq_spend_caps_workspace_provider",
            "workspace_id",
            text("COALESCE(provider, ''::text)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    daily_cap_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    monthly_cap_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class ProviderCredential(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
):
    __tablename__ = "provider_credentials"
    __table_args__ = (
        Index("ix_provider_credentials_workspace", "workspace_id"),
        Index(
            "uq_provider_credentials_workspace_provider_label",
            "workspace_id",
            "provider",
            "label",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    # Ciphertext only — never a plaintext secret. See schema review §6.
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProviderCredentialStatus] = mapped_column(
        SAEnum(
            ProviderCredentialStatus,
            name="provider_credential_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=ProviderCredentialStatus.ACTIVE,
    )
