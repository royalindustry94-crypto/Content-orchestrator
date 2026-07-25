from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    CreatedAtMixin,
    CreatedByMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)
from app.models.enums import ContentLineageRelationship, ContentStage, ContentStatus


class ContentItem(
    Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin, SoftDeleteMixin
):
    __tablename__ = "content_items"
    __table_args__ = (
        Index(
            "ix_content_items_workspace_pillar",
            "workspace_id",
            "pillar_id",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_content_items_workspace_stage",
            "workspace_id",
            "current_stage",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index(
            "ix_content_items_workspace_status",
            "workspace_id",
            "status",
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pillar_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_pillars.id"), nullable=True
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    target_length_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ContentStage.IDEA,
    )
    status: Mapped[ContentStatus] = mapped_column(
        SAEnum(ContentStatus, name="content_status", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
        default=ContentStatus.ACTIVE,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "content_versions.id",
            use_alter=True,
            name="fk_content_items_current_version",
        ),
        nullable=True,
    )
    current_pipeline_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(
            "pipeline_runs.id",
            use_alter=True,
            name="fk_content_items_current_run",
        ),
        nullable=True,
    )


class ContentVersion(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    """Immutable. Each script (re)generation is a new row."""

    __tablename__ = "content_versions"
    __table_args__ = (
        Index("ix_content_versions_item", "content_item_id", text("created_at DESC")),
        Index("ix_content_versions_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    script_hook: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    script_cta: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_by: Mapped[str | None] = mapped_column(Text, nullable=True)


class ContentLineage(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    """Immutable edge recording that one content item was derived from
    another (translated / remixed / clipped / derived). A dedicated table
    (not a self-FK on content_items) so a single source can fan out to many
    derivatives across platforms, each edge carrying its relationship type.
    """

    __tablename__ = "content_lineage"
    __table_args__ = (
        UniqueConstraint(
            "parent_content_item_id",
            "child_content_item_id",
            "relationship_type",
            name="uq_content_lineage_edge",
        ),
        CheckConstraint(
            "parent_content_item_id <> child_content_item_id",
            name="ck_content_lineage_no_self",
        ),
        Index("ix_content_lineage_child", "child_content_item_id"),
        Index("ix_content_lineage_parent", "parent_content_item_id"),
        Index("ix_content_lineage_workspace", "workspace_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    child_content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[ContentLineageRelationship] = mapped_column(
        SAEnum(ContentLineageRelationship, name="content_lineage_relationship", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
