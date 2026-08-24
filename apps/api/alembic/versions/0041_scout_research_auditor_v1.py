"""Scout and Research Auditor V1.

Creates bounded workspace research runs, immutable source provenance and audit
records, deduplicated opportunities, evidence links, and disabled-by-default
research schedule configuration. All tables are tenant-scoped and use the
existing RLS policy helpers; no existing migration is altered.

Revision ID: 0041
Revises: 0040
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

revision: str = "0041"
down_revision: str | None = "0040"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    op.create_table(
        "research_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("research_objective", sa.Text(), nullable=False),
        sa.Column("permitted_sources", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_searches", sa.Integer(), nullable=False),
        sa.Column("max_provider_calls", sa.Integer(), nullable=False),
        sa.Column("max_tokens", sa.Integer(), nullable=False),
        sa.Column("max_cost_usd", sa.Numeric(10, 4), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="queued"),
        sa.Column("provider_state", sa.Text(), nullable=False, server_default="not_configured"),
        sa.Column("searches_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_calls_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tokens_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("reserved_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("actual_cost_usd", sa.Numeric(10, 4), nullable=False, server_default="0"),
        sa.Column("opportunity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("audited_opportunity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_opportunity_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("max_searches > 0 AND max_provider_calls >= 0 AND max_tokens >= 0 AND max_cost_usd >= 0 AND max_attempts > 0", name="ck_research_runs_bounds"),
    )
    op.create_index("ix_research_runs_workspace_created", "research_runs", ["workspace_id", "created_at"])
    op.create_index("ix_research_runs_workspace_status", "research_runs", ["workspace_id", "status"])
    op.create_index("ix_research_runs_workspace_correlation", "research_runs", ["workspace_id", "correlation_id"])

    op.create_table(
        "research_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("claim_supported", sa.Text(), nullable=True),
        sa.Column("freshness", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("content_digest", sa.Text(), nullable=False),
        sa.Column("safe_excerpt", sa.Text(), nullable=True),
        sa.Column("handling_state", sa.Text(), nullable=False, server_default="accepted"),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("workspace_id", "research_run_id", "canonical_url", name="uq_research_source_run_url"),
    )
    op.create_index("ix_research_sources_workspace_run", "research_sources", ["workspace_id", "research_run_id"])
    op.create_index("ix_research_sources_workspace_digest", "research_sources", ["workspace_id", "content_digest"])

    op.create_table(
        "opportunities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_runs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("proposed_angle", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=True),
        sa.Column("target_platform", sa.Text(), nullable=True),
        sa.Column("suggested_format", sa.Text(), nullable=True),
        sa.Column("discovered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("freshness", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("risk", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("status", sa.Text(), nullable=False, server_default="watching"),
        sa.Column("created_by_worker", sa.Text(), nullable=False, server_default="scout"),
        sa.Column("component_scores", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("score_reasoning", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("dedupe_key", sa.Text(), nullable=False),
        sa.Column("audit_gate_status", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("performance_data_state", sa.Text(), nullable=False, server_default="no_performance_data"),
        sa.Column("strategist_state", sa.Text(), nullable=False, server_default="not_sent"),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("workspace_id", "dedupe_key", name="uq_opportunities_workspace_dedupe"),
    )
    op.create_index("ix_opportunities_workspace_status", "opportunities", ["workspace_id", "status"])
    op.create_index("ix_opportunities_workspace_run", "opportunities", ["workspace_id", "research_run_id"])
    op.create_index("ix_opportunities_workspace_topic", "opportunities", ["workspace_id", "topic"])

    op.create_table(
        "opportunity_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_sources.id", ondelete="CASCADE"), nullable=False),
        sa.Column("claim_supported", sa.Text(), nullable=False),
        sa.Column("relevance", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("contradiction_flag", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("workspace_id", "opportunity_id", "source_id", name="uq_opportunity_evidence_link"),
    )
    op.create_index("ix_opportunity_evidence_workspace_opportunity", "opportunity_evidence", ["workspace_id", "opportunity_id"])

    op.create_table(
        "research_audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("opportunity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("research_run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("research_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="not_run"),
        sa.Column("evaluator_context_version", sa.Text(), nullable=False, server_default="research-auditor-v1"),
        sa.Column("scout_snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("warnings", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("blocked_reasons", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("test_data", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_research_audits_workspace_opportunity_checked", "research_audits", ["workspace_id", "opportunity_id", "checked_at"])
    op.create_index("ix_research_audits_workspace_run", "research_audits", ["workspace_id", "research_run_id"])

    op.create_table(
        "research_schedules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("frequency", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("enabled_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("workspace_id", name="uq_research_schedule_workspace"),
    )

    for table in ("research_runs", "opportunities", "research_schedules"):
        attach_version_trigger(table)
        enable_rls(table)
        grant_runtime(table)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)
        policy_update_roles(table, _EDIT)

    for table in ("research_sources", "opportunity_evidence", "research_audits"):
        attach_immutable_trigger(table)
        attach_immutable_delete_trigger(table)
        enable_rls(table)
        grant_runtime(table, update=False, delete=False)
        policy_select_members(table, _ALL)
        policy_insert_roles(table, _EDIT)


def downgrade() -> None:
    for table in ("research_audits", "opportunity_evidence", "research_sources"):
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable ON {table};")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_immutable_delete ON {table};")
    for table in ("research_schedules", "opportunities", "research_runs"):
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_insert_roles ON {table};")
        op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
        op.execute(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute(f"DROP TRIGGER IF EXISTS trg_{table}_version ON {table};")
    op.drop_table("research_schedules")
    op.drop_table("research_audits")
    op.drop_table("opportunity_evidence")
    op.drop_table("opportunities")
    op.drop_table("research_sources")
    op.drop_table("research_runs")
