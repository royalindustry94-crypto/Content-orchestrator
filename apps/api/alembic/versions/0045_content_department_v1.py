"""Create bounded independently audited Content Department V1 records.

Revision ID: 0045
Revises: 0044
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

revision: str = "0045"
down_revision: str | None = "0044"
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


def upgrade() -> None:
    op.create_table(
        "content_department_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "strategy_brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("trigger", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("provider_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("business_context_state", sa.Text(), nullable=False, server_default="incomplete"),
        sa.Column("max_provider_calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="900"),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("creative_directions_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("packages_ready", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("packages_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
        sa.CheckConstraint(
            "max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0 AND timeout_seconds > 0",
            name="ck_content_department_run_bounds",
        ),
    )
    op.create_index(
        "ix_content_department_runs_workspace_created",
        "content_department_runs",
        ["workspace_id", "created_at"],
    )
    op.create_index(
        "ix_content_department_runs_workspace_status",
        "content_department_runs",
        ["workspace_id", "status"],
    )
    op.create_index(
        "ix_content_department_runs_workspace_strategy",
        "content_department_runs",
        ["workspace_id", "strategy_brief_id"],
    )
    op.create_index(
        "ix_content_department_runs_correlation",
        "content_department_runs",
        ["workspace_id", "correlation_id"],
    )
    op.create_index(
        "ix_content_department_runs_strategy", "content_department_runs", ["strategy_brief_id"]
    )
    op.create_index(
        "ix_content_department_runs_created_by", "content_department_runs", ["created_by"]
    )
    op.create_index(
        "ix_content_department_runs_updated_by", "content_department_runs", ["updated_by"]
    )

    op.create_table(
        "creative_directions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_department_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_department_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "strategy_brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("target_platform", sa.Text(), nullable=True),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("creative_concept", sa.Text(), nullable=False),
        sa.Column("opening_pattern", sa.Text(), nullable=True),
        sa.Column("hook_direction", sa.Text(), nullable=True),
        sa.Column("story_structure", sa.Text(), nullable=True),
        sa.Column("tone", sa.Text(), nullable=True),
        sa.Column("pacing", sa.Text(), nullable=True),
        sa.Column("visual_direction", sa.Text(), nullable=True),
        sa.Column("audio_direction", sa.Text(), nullable=True),
        sa.Column("cta_direction", sa.Text(), nullable=True),
        sa.Column("desired_emotion", sa.Text(), nullable=True),
        sa.Column(
            "required_claims",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "prohibited_claims",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "required_assets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("estimated_duration", sa.Text(), nullable=True),
        sa.Column("production_complexity", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column(
            "risk_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("worker_id", sa.Text(), nullable=False, server_default="creative_director"),
        sa.Column("provider", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column(
            "prompt_version", sa.Text(), nullable=False, server_default="creative-director-v1"
        ),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created_by_columns(),
    )
    op.create_index(
        "ix_creative_directions_workspace_strategy",
        "creative_directions",
        ["workspace_id", "strategy_brief_id"],
    )
    op.create_index(
        "ix_creative_directions_workspace_run",
        "creative_directions",
        ["workspace_id", "content_department_run_id"],
    )
    op.create_index(
        "ix_creative_directions_workspace_status", "creative_directions", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_creative_directions_run", "creative_directions", ["content_department_run_id"]
    )
    op.create_index("ix_creative_directions_strategy", "creative_directions", ["strategy_brief_id"])
    op.create_index("ix_creative_directions_created_by", "creative_directions", ["created_by"])

    op.create_table(
        "content_packages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_department_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_department_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "creative_direction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("creative_directions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "strategy_brief_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_briefs.id", ondelete="RESTRICT"),
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
            sa.ForeignKey("content_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "prior_content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("revision_reason", sa.Text(), nullable=True),
        sa.Column("writer_worker_id", sa.Text(), nullable=False, server_default="writer"),
        sa.Column("provider", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("model", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False, server_default="writer-v1"),
        sa.Column(
            "input_references",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "package_fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "status", sa.Text(), nullable=False, server_default="writer_provider_not_configured"
        ),
        sa.Column("audit_gate_status", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("producer_handoff_state", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        *_actor_columns(),
        sa.UniqueConstraint(
            "workspace_id", "content_version_id", name="uq_content_package_version"
        ),
    )
    op.create_index(
        "ix_content_packages_workspace_status", "content_packages", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_content_packages_workspace_item",
        "content_packages",
        ["workspace_id", "content_item_id"],
    )
    op.create_index(
        "ix_content_packages_workspace_direction",
        "content_packages",
        ["workspace_id", "creative_direction_id"],
    )
    op.create_index("ix_content_packages_run", "content_packages", ["content_department_run_id"])
    op.create_index("ix_content_packages_strategy", "content_packages", ["strategy_brief_id"])
    op.create_index("ix_content_packages_item", "content_packages", ["content_item_id"])
    op.create_index("ix_content_packages_version", "content_packages", ["content_version_id"])
    op.create_index(
        "ix_content_packages_prior_version", "content_packages", ["prior_content_version_id"]
    )
    op.create_index("ix_content_packages_direction", "content_packages", ["creative_direction_id"])
    op.create_index("ix_content_packages_created_by", "content_packages", ["created_by"])
    op.create_index("ix_content_packages_updated_by", "content_packages", ["updated_by"])

    op.create_table(
        "content_claims",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_type", sa.Text(), nullable=False),
        sa.Column("source_required", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "supporting_evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("verification_status", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("risk", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("freshness", sa.Text(), nullable=True),
        sa.Column("evidence_reasoning", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
    )
    op.create_index(
        "ix_content_claims_workspace_version",
        "content_claims",
        ["workspace_id", "content_version_id"],
    )
    op.create_index(
        "ix_content_claims_workspace_status",
        "content_claims",
        ["workspace_id", "verification_status"],
    )
    op.create_index("ix_content_claims_package", "content_claims", ["content_package_id"])
    op.create_index("ix_content_claims_version", "content_claims", ["content_version_id"])
    op.create_index("ix_content_claims_created_by", "content_claims", ["created_by"])
    op.create_index("ix_content_claims_updated_by", "content_claims", ["updated_by"])

    op.create_table(
        "content_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("auditor_type", sa.Text(), nullable=False),
        sa.Column("auditor_worker_id", sa.Text(), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column(
            "artifact_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "requirements_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "blocked_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column(
            "retry_history",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_content_audits_workspace_package_checked",
        "content_audits",
        ["workspace_id", "content_package_id", "checked_at"],
    )
    op.create_index(
        "ix_content_audits_workspace_version_type",
        "content_audits",
        ["workspace_id", "content_version_id", "auditor_type"],
    )
    op.create_index("ix_content_audits_package", "content_audits", ["content_package_id"])
    op.create_index("ix_content_audits_version", "content_audits", ["content_version_id"])

    op.create_table(
        "content_audit_invalidations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_audit_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_audits.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "affected_dimensions",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        *_created_by_columns(),
        sa.UniqueConstraint(
            "content_audit_id", "content_version_id", name="uq_content_audit_invalidation"
        ),
    )
    op.create_index(
        "ix_content_audit_invalidations_workspace_version",
        "content_audit_invalidations",
        ["workspace_id", "content_version_id"],
    )
    op.create_index(
        "ix_content_audit_invalidations_audit", "content_audit_invalidations", ["content_audit_id"]
    )
    op.create_index(
        "ix_content_audit_invalidations_package",
        "content_audit_invalidations",
        ["content_package_id"],
    )
    op.create_index(
        "ix_content_audit_invalidations_version",
        "content_audit_invalidations",
        ["content_version_id"],
    )
    op.create_index(
        "ix_content_audit_invalidations_created_by", "content_audit_invalidations", ["created_by"]
    )

    op.create_table(
        "originality_fingerprints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_package_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_packages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "content_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("content_versions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("text_fingerprint", sa.Text(), nullable=False),
        sa.Column("hook_fingerprint", sa.Text(), nullable=False),
        sa.Column("structure_fingerprint", sa.Text(), nullable=False),
        sa.Column("semantic_reference", sa.Text(), nullable=True),
        sa.Column(
            "comparison_set",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "similarity_findings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_created_by_columns(),
        sa.UniqueConstraint(
            "workspace_id", "content_version_id", name="uq_originality_fingerprint_version"
        ),
    )
    op.create_index(
        "ix_originality_fingerprints_workspace_text",
        "originality_fingerprints",
        ["workspace_id", "text_fingerprint"],
    )
    op.create_index(
        "ix_originality_fingerprints_workspace_hook",
        "originality_fingerprints",
        ["workspace_id", "hook_fingerprint"],
    )
    op.create_index(
        "ix_originality_fingerprints_workspace_structure",
        "originality_fingerprints",
        ["workspace_id", "structure_fingerprint"],
    )
    op.create_index(
        "ix_originality_fingerprints_package", "originality_fingerprints", ["content_package_id"]
    )
    op.create_index(
        "ix_originality_fingerprints_version", "originality_fingerprints", ["content_version_id"]
    )
    op.create_index(
        "ix_originality_fingerprints_created_by", "originality_fingerprints", ["created_by"]
    )

    for table in ("content_department_runs", "content_packages", "content_claims"):
        attach_version_trigger(table)
        enable_rls(table)
        grant_runtime(table)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)
        policy_update_roles(table, _EDIT)

    for table in (
        "creative_directions",
        "content_audits",
        "content_audit_invalidations",
        "originality_fingerprints",
    ):
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)
        enable_rls(table)
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)


def downgrade() -> None:
    immutable = (
        "originality_fingerprints",
        "content_audit_invalidations",
        "content_audits",
        "creative_directions",
    )
    mutable = ("content_claims", "content_packages", "content_department_runs")
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
    op.drop_table("originality_fingerprints")
    op.drop_table("content_audit_invalidations")
    op.drop_table("content_audits")
    op.drop_table("content_claims")
    op.drop_table("content_packages")
    op.drop_table("creative_directions")
    op.drop_table("content_department_runs")
