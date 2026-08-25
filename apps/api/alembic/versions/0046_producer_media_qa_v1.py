"""Create bounded Producer and independently audited Media QA records.

Revision ID: 0046
Revises: 0045
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

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def _actor_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True
        ),
        sa.Column(
            "updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
    ]


def _created_by_columns() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True
        ),
    ]


def _json(default: str) -> sa.Column:
    return sa.Column(
        postgresql.JSONB(astext_type=sa.Text()),
        nullable=False,
        server_default=sa.text(default),
    )


def _workspace() -> sa.Column:
    return sa.Column(
        "workspace_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "production_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "content_package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_packages.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "pipeline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("pipeline_runs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("producer_worker_id", sa.Text(), nullable=False, server_default="producer"),
        sa.Column("target_platform", sa.Text(), nullable=True),
        sa.Column("target_format", sa.Text(), nullable=True),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=True),
        sa.Column(
            "required_assets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "provider_plan",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("provider_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("max_provider_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_render_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("max_total_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_repair_cycles", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("render_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("repair_cycles_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
        sa.CheckConstraint(
            "max_provider_calls >= 0 AND max_render_calls >= 0 AND max_cost_usd >= 0 AND max_total_cost_usd >= 0 AND max_attempts > 0 AND max_repair_cycles >= 0 AND timeout_seconds > 0",
            name="ck_production_job_bounds",
        ),
    )
    for name, columns in (
        ("ix_production_jobs_workspace_created", ["workspace_id", "created_at"]),
        ("ix_production_jobs_workspace_status", ["workspace_id", "status"]),
        ("ix_production_jobs_workspace_package", ["workspace_id", "content_package_id"]),
        ("ix_production_jobs_workspace_version", ["workspace_id", "content_version_id"]),
        ("ix_production_jobs_package", ["content_package_id"]),
        ("ix_production_jobs_item", ["content_item_id"]),
        ("ix_production_jobs_version", ["content_version_id"]),
        ("ix_production_jobs_pipeline", ["pipeline_run_id"]),
        ("ix_production_jobs_created_by", ["created_by"]),
        ("ix_production_jobs_updated_by", ["updated_by"]),
    ):
        op.create_index(name, "production_jobs", columns)

    op.create_table(
        "production_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "production_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("production_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("asset_type", sa.Text(), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("provider_job_id", sa.Text(), nullable=True),
        sa.Column(
            "source_inputs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "generation_settings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("model_version", sa.Text(), nullable=True),
        sa.Column("file_hash", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column(
            "dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created_by_columns(),
        sa.UniqueConstraint("workspace_id", "asset_id", name="uq_production_asset_asset"),
    )
    for name, columns in (
        ("ix_production_assets_workspace_job", ["workspace_id", "production_job_id"]),
        ("ix_production_assets_workspace_version", ["workspace_id", "content_version_id"]),
        ("ix_production_assets_job", ["production_job_id"]),
        ("ix_production_assets_asset", ["asset_id"]),
        ("ix_production_assets_version", ["content_version_id"]),
        ("ix_production_assets_created_by", ["created_by"]),
    ):
        op.create_index(name, "production_assets", columns)

    op.create_table(
        "final_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "production_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("production_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "content_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "render_asset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("assets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("render_provider", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("render_job_id", sa.Text(), nullable=True),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column(
            "storage_reference",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("duration_seconds", sa.Numeric(12, 3), nullable=True),
        sa.Column(
            "resolution",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("aspect_ratio", sa.Text(), nullable=True),
        sa.Column("container", sa.Text(), nullable=True),
        sa.Column("codec", sa.Text(), nullable=True),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created_by_columns(),
        sa.UniqueConstraint("workspace_id", "artifact_hash", name="uq_final_artifact_hash"),
    )
    for name, columns in (
        ("ix_final_artifacts_workspace_job", ["workspace_id", "production_job_id"]),
        ("ix_final_artifacts_workspace_version", ["workspace_id", "content_version_id"]),
        ("ix_final_artifacts_job", ["production_job_id"]),
        ("ix_final_artifacts_version", ["content_version_id"]),
        ("ix_final_artifacts_created_by", ["created_by"]),
    ):
        op.create_index(name, "final_artifacts", columns)

    op.create_table(
        "media_qa_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_hash", sa.Text(), nullable=False),
        sa.Column("auditor_worker_id", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column(
            "checks_run",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "visual_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "audio_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "subtitle_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "script_alignment",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "platform_check",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "package_alignment",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "recommended_repair",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("final_artifact_id", "artifact_hash", name="uq_media_qa_artifact_hash"),
    )
    for name, columns in (
        ("ix_media_qa_workspace_artifact", ["workspace_id", "final_artifact_id"]),
        ("ix_media_qa_workspace_status", ["workspace_id", "status"]),
        ("ix_media_qa_artifact", ["final_artifact_id"]),
    ):
        op.create_index(name, "media_qa_results", columns)

    op.create_table(
        "production_repairs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "production_job_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("production_jobs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "media_qa_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_qa_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("affected_component", sa.Text(), nullable=False),
        sa.Column(
            "finding_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("repair_operation", sa.Text(), nullable=False),
        sa.Column("repair_cycle", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "result_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created_by_columns(),
    )
    for name, columns in (
        ("ix_production_repairs_workspace_job", ["workspace_id", "production_job_id"]),
        ("ix_production_repairs_workspace_artifact", ["workspace_id", "final_artifact_id"]),
        ("ix_production_repairs_job", ["production_job_id"]),
        ("ix_production_repairs_artifact", ["final_artifact_id"]),
        ("ix_production_repairs_qa", ["media_qa_result_id"]),
        ("ix_production_repairs_created_by", ["created_by"]),
    ):
        op.create_index(name, "production_repairs", columns)

    op.create_table(
        "artifact_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "media_qa_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_qa_results.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "affected_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        *_created_by_columns(),
        sa.UniqueConstraint("final_artifact_id", "reason", name="uq_artifact_invalidation_reason"),
    )
    for name, columns in (
        ("ix_artifact_invalidations_workspace_artifact", ["workspace_id", "final_artifact_id"]),
        ("ix_artifact_invalidations_qa", ["media_qa_result_id"]),
        ("ix_artifact_invalidations_created_by", ["created_by"]),
    ):
        op.create_index(name, "artifact_invalidations", columns)

    op.create_table(
        "production_readiness",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        _workspace(),
        sa.Column(
            "final_artifact_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("final_artifacts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("media_qa_state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("compliance_state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("chief_audit_state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("human_review_state", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column("status", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column(
            "blocking_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("total_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
        sa.UniqueConstraint(
            "workspace_id", "final_artifact_id", name="uq_production_readiness_artifact"
        ),
    )
    for name, columns in (
        ("ix_production_readiness_workspace_artifact", ["workspace_id", "final_artifact_id"]),
        ("ix_production_readiness_workspace_status", ["workspace_id", "status"]),
        ("ix_production_readiness_artifact", ["final_artifact_id"]),
        ("ix_production_readiness_created_by", ["created_by"]),
        ("ix_production_readiness_updated_by", ["updated_by"]),
    ):
        op.create_index(name, "production_readiness", columns)

    for table in ("production_jobs", "production_readiness"):
        attach_version_trigger(table)
        enable_rls(table)
        grant_runtime(table)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)
        policy_update_roles(table, _EDIT)

    for table in (
        "production_assets",
        "final_artifacts",
        "media_qa_results",
        "production_repairs",
        "artifact_invalidations",
    ):
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)
        enable_rls(table)
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)


def downgrade() -> None:
    immutable = (
        "artifact_invalidations",
        "production_repairs",
        "media_qa_results",
        "final_artifacts",
        "production_assets",
    )
    mutable = ("production_readiness", "production_jobs")
    for table in immutable:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete ON {table};")
    for table in mutable:
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_version ON {table};")
    for table in (
        "production_readiness",
        "artifact_invalidations",
        "production_repairs",
        "media_qa_results",
        "final_artifacts",
        "production_assets",
        "production_jobs",
    ):
        op.drop_table(table)
