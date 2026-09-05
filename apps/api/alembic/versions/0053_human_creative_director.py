"""Add provider-neutral Human Creative Director planning records.

Revision ID: 0053
Revises: 0052

Downgrade drops all Creative Director planning history and is data-destructive.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_delete_trigger,
    attach_immutable_trigger,
    attach_version_trigger,
    enable_rls,
    grant_runtime,
    policy_insert_roles,
    policy_select_members,
    policy_update_roles,
)

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_READ = ["admin", "editor", "reviewer", "viewer"]
_AUTHOR = ["admin", "editor"]
_REVIEW = ["admin", "reviewer"]


def _workspace() -> sa.Column:
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def _created_by() -> sa.Column:
    return sa.Column(
        "created_by",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("profiles.id"),
        nullable=True,
    )


def upgrade() -> None:
    op.create_table(
        "creative_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("desired_outcome", sa.Text(), nullable=False),
        sa.Column(
            "status", sa.String(length=32), nullable=False, server_default="brief_ready"
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id"),
            nullable=True,
        ),
        _created_at(),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("workspace_id", "id", name="uq_creative_projects_workspace_id"),
        sa.CheckConstraint(
            "status IN ('brief_ready','prompt_review','archived')",
            name="ck_creative_projects_status",
        ),
    )
    for name, columns in (
        ("ix_creative_projects_workspace_created", ["workspace_id", "created_at"]),
        ("ix_creative_projects_workspace_status", ["workspace_id", "status"]),
        ("ix_creative_projects_created_by", ["created_by"]),
        ("ix_creative_projects_updated_by", ["updated_by"]),
    ):
        op.create_index(name, "creative_projects", columns)

    op.create_table(
        "creative_brief_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("customer_request", sa.Text(), nullable=False),
        sa.Column(
            "requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "exclusions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("reference_notes", sa.Text(), nullable=True),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        _created_by(),
        _created_at(),
        sa.UniqueConstraint("workspace_id", "id", name="uq_creative_briefs_workspace_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "revision_number",
            name="uq_creative_briefs_project_revision",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_creative_briefs_workspace_project",
        ),
        sa.CheckConstraint("revision_number > 0", name="ck_creative_briefs_revision"),
        sa.CheckConstraint(
            "char_length(fingerprint) = 64", name="ck_creative_briefs_fingerprint"
        ),
    )
    for name, columns in (
        ("ix_creative_briefs_workspace_project", ["workspace_id", "project_id"]),
        ("ix_creative_briefs_project", ["project_id"]),
        ("ix_creative_briefs_created_by", ["created_by"]),
    ):
        op.create_index(name, "creative_brief_versions", columns)

    op.create_table(
        "prompt_pack_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("brief_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("target_tool", sa.String(length=100), nullable=True),
        sa.Column(
            "prompt_spec",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "continuity_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "negative_prompts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "validation_checklist",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("estimated_generation_count", sa.Integer(), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        _created_by(),
        _created_at(),
        sa.UniqueConstraint("workspace_id", "id", name="uq_prompt_packs_workspace_id"),
        sa.UniqueConstraint(
            "workspace_id",
            "id",
            "fingerprint",
            name="uq_prompt_packs_workspace_fingerprint",
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "project_id",
            "revision_number",
            name="uq_prompt_packs_project_revision",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_prompt_packs_workspace_project",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "brief_version_id"],
            ["creative_brief_versions.workspace_id", "creative_brief_versions.id"],
            ondelete="RESTRICT",
            name="fk_prompt_packs_workspace_brief",
        ),
        sa.CheckConstraint("revision_number > 0", name="ck_prompt_packs_revision"),
        sa.CheckConstraint(
            "estimated_generation_count >= 1", name="ck_prompt_packs_generation_count"
        ),
        sa.CheckConstraint(
            "char_length(fingerprint) = 64", name="ck_prompt_packs_fingerprint"
        ),
    )
    for name, columns in (
        ("ix_prompt_packs_workspace_project", ["workspace_id", "project_id"]),
        ("ix_prompt_packs_project", ["project_id"]),
        ("ix_prompt_packs_brief", ["brief_version_id"]),
        ("ix_prompt_packs_created_by", ["created_by"]),
    ):
        op.create_index(name, "prompt_pack_versions", columns)

    op.create_table(
        "prompt_pack_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_pack_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("prompt_pack_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "reviewer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        _created_at(),
        sa.UniqueConstraint(
            "workspace_id",
            "prompt_pack_version_id",
            name="uq_prompt_decisions_pack",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "project_id"],
            ["creative_projects.workspace_id", "creative_projects.id"],
            ondelete="CASCADE",
            name="fk_prompt_decisions_workspace_project",
        ),
        sa.ForeignKeyConstraint(
            ["workspace_id", "prompt_pack_version_id", "prompt_pack_fingerprint"],
            [
                "prompt_pack_versions.workspace_id",
                "prompt_pack_versions.id",
                "prompt_pack_versions.fingerprint",
            ],
            ondelete="RESTRICT",
            name="fk_prompt_decisions_exact_pack",
        ),
        sa.CheckConstraint(
            "decision IN ('approved','changes_requested')",
            name="ck_prompt_pack_decisions_decision",
        ),
        sa.CheckConstraint(
            "char_length(prompt_pack_fingerprint) = 64",
            name="ck_prompt_pack_decisions_fingerprint",
        ),
    )
    for name, columns in (
        ("ix_prompt_decisions_workspace_project", ["workspace_id", "project_id"]),
        ("ix_prompt_decisions_project", ["project_id"]),
        ("ix_prompt_decisions_pack", ["prompt_pack_version_id"]),
        ("ix_prompt_decisions_reviewer", ["reviewer_id"]),
    ):
        op.create_index(name, "prompt_pack_decisions", columns)

    attach_version_trigger("creative_projects")
    for table in ("creative_brief_versions", "prompt_pack_versions", "prompt_pack_decisions"):
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)

    for table in (
        "creative_projects",
        "creative_brief_versions",
        "prompt_pack_versions",
        "prompt_pack_decisions",
    ):
        enable_rls(table)

    grant_runtime("creative_projects", delete=False)
    policy_select_members("creative_projects", _READ)
    policy_insert_roles("creative_projects", _AUTHOR)
    policy_update_roles("creative_projects", _AUTHOR)

    for table in ("creative_brief_versions", "prompt_pack_versions"):
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _READ)
        policy_insert_roles(table, _AUTHOR)

    grant_runtime("prompt_pack_decisions", update=False, delete=False)
    policy_select_members("prompt_pack_decisions", _READ)
    policy_insert_roles("prompt_pack_decisions", _REVIEW)


def downgrade() -> None:
    op.drop_table("prompt_pack_decisions")
    op.drop_table("prompt_pack_versions")
    op.drop_table("creative_brief_versions")
    op.drop_table("creative_projects")
