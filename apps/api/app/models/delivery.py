from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)
from app.models.enums import AssetSource, AssetStatus, AssetType, PublishJobStatus


class Asset(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin):
    __tablename__ = "assets"
    __table_args__ = (
        Index(
            "ix_assets_item_type",
            "content_item_id",
            "type",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("ix_assets_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    content_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_versions.id"), nullable=True
    )
    type: Mapped[AssetType] = mapped_column(
        SAEnum(
            AssetType,
            name="asset_type",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    source: Mapped[AssetSource] = mapped_column(
        SAEnum(
            AssetSource,
            name="asset_source",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    status: Mapped[AssetStatus] = mapped_column(
        SAEnum(
            AssetStatus,
            name="asset_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=AssetStatus.PENDING,
    )
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Storage metadata — provider-agnostic source of truth for the stored
    # object (url above is a resolved/public URL). All nullable: a pending
    # asset has no stored object yet.
    storage_provider: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_bucket: Mapped[str | None] = mapped_column(Text, nullable=True)
    storage_object_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum_algorithm: Mapped[str | None] = mapped_column(Text, nullable=True)
    mime_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    # Provider-specific generation attributes without a column per provider.
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PublishJob(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
):
    """Scheduled publish + its execution outcome."""

    __tablename__ = "publish_jobs"
    __table_args__ = (
        Index("ix_publish_jobs_item", "content_item_id"),
        Index("ix_publish_jobs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_publish_jobs_workspace_time",
            "workspace_id",
            "scheduled_time",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "uq_publish_jobs_workspace_idem",
            "workspace_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    scheduled_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Dedup key so a retried "schedule publish" request can't create a
    # duplicate job. Unique per workspace when present.
    idempotency_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PublishJobStatus] = mapped_column(
        SAEnum(
            PublishJobStatus,
            name="publish_job_status",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
        default=PublishJobStatus.PENDING,
    )
    external_post_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
