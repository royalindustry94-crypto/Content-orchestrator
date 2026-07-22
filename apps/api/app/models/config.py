from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Numeric, String, Text
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

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)


class SpendCap(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "spend_caps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str | None] = mapped_column(String, nullable=True)
    daily_cap_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    monthly_cap_usd: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)


class ProviderCredential(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
):
    __tablename__ = "provider_credentials"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    label: Mapped[str] = mapped_column(String, nullable=False)
    # Ciphertext only — never a plaintext secret. See schema review §6.
    encrypted_secret: Mapped[str] = mapped_column(Text, nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ProviderCredentialStatus] = mapped_column(
        SAEnum(ProviderCredentialStatus, name="provider_credential_status", native_enum=True),
        nullable=False,
        default=ProviderCredentialStatus.ACTIVE,
    )
