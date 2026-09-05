"""Provider-neutral Human Creative Director records.

Briefs, prompt packs, and decisions are append-only. A decision authorizes only
the exact prompt-pack fingerprint it references; it is not publication approval.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    CreatedAtMixin,
    CreatedByMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)


class CreativeProject(Base, WorkspaceScopedMixin, TimestampMixin, ActorMixin, VersionMixin):
    __tablename__ = "creative_projects"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_creative_projects_workspace_id"),
        CheckConstraint(
            "status IN ('brief_ready','prompt_review','archived')",
            name="ck_creative_projects_status",
        ),
        Index("ix_creative_projects_workspace_created", "workspace_id", "created_at"),
        Index("ix_creative_projects_workspace_status", "workspace_id", "status"),
        Index("ix_creative_projects_created_by", "created_by"),
        Index("ix_creative_projects_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    desired_outcome: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="brief_ready")


class CreativeBriefVersion(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "creative_brief_versions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_creative_briefs_workspace_id"),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "revision_number",
            name="uq_creative_briefs_project_revision",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_creative_briefs_workspace_project",
        ),
        CheckConstraint("revision_number > 0", name="ck_creative_briefs_revision"),
        CheckConstraint("char_length(fingerprint) = 64", name="ck_creative_briefs_fingerprint"),
        Index("ix_creative_briefs_workspace_project", "workspace_id", "project_id"),
        Index("ix_creative_briefs_project", "project_id"),
        Index("ix_creative_briefs_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    customer_request: Mapped[str] = mapped_column(Text, nullable=False)
    requirements: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    exclusions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reference_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class PromptPackVersion(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "prompt_pack_versions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "id", name="uq_prompt_packs_workspace_id"),
        UniqueConstraint(
            "workspace_id",
            "id",
            "fingerprint",
            name="uq_prompt_packs_workspace_fingerprint",
        ),
        UniqueConstraint(
            "workspace_id",
            "project_id",
            "revision_number",
            name="uq_prompt_packs_project_revision",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_prompt_packs_workspace_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "brief_version_id"],
            ["creative_brief_versions.workspace_id", "creative_brief_versions.id"],
            ondelete="RESTRICT",
            name="fk_prompt_packs_workspace_brief",
        ),
        CheckConstraint("revision_number > 0", name="ck_prompt_packs_revision"),
        CheckConstraint("estimated_generation_count >= 1", name="ck_prompt_packs_generation_count"),
        CheckConstraint("char_length(fingerprint) = 64", name="ck_prompt_packs_fingerprint"),
        Index("ix_prompt_packs_workspace_project", "workspace_id", "project_id"),
        Index("ix_prompt_packs_project", "project_id"),
        Index("ix_prompt_packs_brief", "brief_version_id"),
        Index("ix_prompt_packs_created_by", "created_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    brief_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    target_tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    prompt_spec: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    continuity_rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    negative_prompts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    validation_checklist: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    estimated_generation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)


class PromptPackDecision(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "prompt_pack_decisions"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "prompt_pack_version_id",
            name="uq_prompt_decisions_pack",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_prompt_decisions_workspace_project",
        ),
        ForeignKeyConstraint(
            ["workspace_id", "prompt_pack_version_id", "prompt_pack_fingerprint"],
            [
                "prompt_pack_versions.workspace_id",
                "prompt_pack_versions.id",
                "prompt_pack_versions.fingerprint",
            ],
            ondelete="RESTRICT",
            name="fk_prompt_decisions_exact_pack",
        ),
        CheckConstraint(
            "decision IN ('approved','changes_requested')",
            name="ck_prompt_pack_decisions_decision",
        ),
        CheckConstraint(
            "char_length(prompt_pack_fingerprint) = 64",
            name="ck_prompt_pack_decisions_fingerprint",
        ),
        Index("ix_prompt_decisions_workspace_project", "workspace_id", "project_id"),
        Index("ix_prompt_decisions_project", "project_id"),
        Index("ix_prompt_decisions_pack", "prompt_pack_version_id"),
        Index("ix_prompt_decisions_fingerprint", "prompt_pack_fingerprint"),
        Index("ix_prompt_decisions_reviewer", "reviewer_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prompt_pack_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    prompt_pack_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    decision: Mapped[str] = mapped_column(String(24), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False
    )
