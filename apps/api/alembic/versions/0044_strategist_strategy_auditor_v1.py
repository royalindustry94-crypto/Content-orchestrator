"""Create bounded Strategist and independent Strategy Auditor V1 records.

Revision ID: 0044
Revises: 0043
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

revision: str = "0044"
down_revision: str | None = "0043"
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


def upgrade() -> None:
    op.create_table(
        "strategy_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("trigger", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("strategy_objective", sa.Text(), nullable=False),
        sa.Column(
            "source_opportunity_ids",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_provider_calls", sa.Integer(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("max_cost_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("provider_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("business_context_state", sa.Text(), nullable=False, server_default="incomplete"),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("briefs_created", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("briefs_passed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("briefs_blocked", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
        sa.CheckConstraint(
            "max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0",
            name="ck_strategy_runs_bounds",
        ),
    )
    op.create_index(
        "ix_strategy_runs_workspace_created", "strategy_runs", ["workspace_id", "created_at"]
    )
    op.create_index(
        "ix_strategy_runs_workspace_status", "strategy_runs", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_strategy_runs_workspace_correlation",
        "strategy_runs",
        ["workspace_id", "correlation_id"],
    )
    op.create_index("ix_strategy_runs_created_by", "strategy_runs", ["created_by"])
    op.create_index("ix_strategy_runs_updated_by", "strategy_runs", ["updated_by"])

    op.create_table(
        "strategy_briefs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "strategy_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("objective", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("target_platform", sa.Text(), nullable=True),
        sa.Column("content_format", sa.Text(), nullable=True),
        sa.Column("creative_angle", sa.Text(), nullable=True),
        sa.Column("core_message", sa.Text(), nullable=True),
        sa.Column("hook_direction", sa.Text(), nullable=True),
        sa.Column("cta_direction", sa.Text(), nullable=True),
        sa.Column("business_goal", sa.Text(), nullable=True),
        sa.Column("success_metric", sa.Text(), nullable=True),
        sa.Column("commercial_goal", sa.Text(), nullable=True),
        sa.Column("estimated_complexity", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("risk_level", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("evidence_summary", sa.Text(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("priority", sa.Text(), nullable=False, server_default="watch"),
        sa.Column(
            "component_scores",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "score_reasoning",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("recommended_length", sa.Text(), nullable=True),
        sa.Column("recommended_posting_window", sa.Text(), nullable=True),
        sa.Column(
            "required_assets",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "production_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "rights_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "compliance_requirements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "estimated_provider_usage",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "estimated_cost_range",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("cost_state", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("capability_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("business_context_state", sa.Text(), nullable=False, server_default="incomplete"),
        sa.Column("performance_data_state", sa.Text(), nullable=False, server_default="no_data"),
        sa.Column("structural_fingerprint", sa.Text(), nullable=False),
        sa.Column("repetition_state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column(
            "repetition_reasons",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("audit_gate_status", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("writer_handoff_state", sa.Text(), nullable=False, server_default="blocked"),
        sa.Column("created_by_worker", sa.Text(), nullable=False, server_default="strategist"),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        *_actor_columns(),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "workspace_id", "structural_fingerprint", name="uq_strategy_briefs_workspace_fp"
        ),
    )
    op.create_index(
        "ix_strategy_briefs_workspace_status", "strategy_briefs", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_strategy_briefs_workspace_run", "strategy_briefs", ["workspace_id", "strategy_run_id"]
    )
    op.create_index(
        "ix_strategy_briefs_workspace_priority", "strategy_briefs", ["workspace_id", "priority"]
    )
    op.create_index(
        "ix_strategy_briefs_workspace_objective",
        "strategy_briefs",
        ["workspace_id", "business_goal"],
    )
    op.create_index("ix_strategy_briefs_run", "strategy_briefs", ["strategy_run_id"])
    op.create_index("ix_strategy_briefs_created_by", "strategy_briefs", ["created_by"])
    op.create_index("ix_strategy_briefs_updated_by", "strategy_briefs", ["updated_by"])

    op.create_table(
        "strategy_brief_opportunities",
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
            sa.ForeignKey("strategy_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "opportunity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("opportunities.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "workspace_id",
            "strategy_brief_id",
            "opportunity_id",
            name="uq_strategy_brief_opportunity",
        ),
    )
    op.create_index(
        "ix_strategy_brief_opportunities_workspace_brief",
        "strategy_brief_opportunities",
        ["workspace_id", "strategy_brief_id"],
    )
    op.create_index(
        "ix_strategy_brief_opportunities_brief",
        "strategy_brief_opportunities",
        ["strategy_brief_id"],
    )
    op.create_index(
        "ix_strategy_brief_opportunities_opportunity",
        "strategy_brief_opportunities",
        ["opportunity_id"],
    )

    op.create_table(
        "strategy_audits",
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
            sa.ForeignKey("strategy_briefs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "strategy_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("strategy_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column(
            "evaluator_context_version",
            sa.Text(),
            nullable=False,
            server_default="strategy-auditor-v1",
        ),
        sa.Column(
            "brief_snapshot",
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
            "checked_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
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
        "ix_strategy_audits_workspace_brief_checked",
        "strategy_audits",
        ["workspace_id", "strategy_brief_id", "checked_at"],
    )
    op.create_index(
        "ix_strategy_audits_workspace_run", "strategy_audits", ["workspace_id", "strategy_run_id"]
    )
    op.create_index("ix_strategy_audits_brief", "strategy_audits", ["strategy_brief_id"])
    op.create_index("ix_strategy_audits_run", "strategy_audits", ["strategy_run_id"])

    op.create_table(
        "strategy_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workspace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("frequency", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "enabled_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True
        ),
        *_actor_columns(),
        sa.UniqueConstraint("workspace_id", name="uq_strategy_schedule_workspace"),
    )
    op.create_index("ix_strategy_schedules_created_by", "strategy_schedules", ["created_by"])
    op.create_index("ix_strategy_schedules_enabled_by", "strategy_schedules", ["enabled_by"])
    op.create_index("ix_strategy_schedules_updated_by", "strategy_schedules", ["updated_by"])

    for table in ("strategy_runs", "strategy_briefs", "strategy_schedules"):
        attach_version_trigger(table)
        enable_rls(table)
        grant_runtime(table)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)
        policy_update_roles(table, _EDIT)

    for table in ("strategy_brief_opportunities", "strategy_audits"):
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)
        enable_rls(table)
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)


def downgrade() -> None:
    for table in ("strategy_audits", "strategy_brief_opportunities"):
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete ON {table};")
    for table in ("strategy_schedules", "strategy_briefs", "strategy_runs"):
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_version ON {table};")
    op.drop_table("strategy_schedules")
    op.drop_table("strategy_audits")
    op.drop_table("strategy_brief_opportunities")
    op.drop_table("strategy_briefs")
    op.drop_table("strategy_runs")
