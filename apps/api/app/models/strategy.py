"""Bounded Strategist and independent Strategy Auditor V1 records."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import (
    ActorMixin,
    Base,
    CreatedAtMixin,
    SoftDeleteMixin,
    TimestampMixin,
    VersionMixin,
    WorkspaceScopedMixin,
)


def _utcnow() -> datetime:
    return datetime.now(UTC)


class StrategyRun(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin, ActorMixin):
    __tablename__ = "strategy_runs"
    __table_args__ = (
        Index("ix_strategy_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_strategy_runs_workspace_status", "workspace_id", "status"),
        Index("ix_strategy_runs_workspace_correlation", "workspace_id", "correlation_id"),
        Index("ix_strategy_runs_created_by", "created_by"),
        Index("ix_strategy_runs_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    strategy_objective: Mapped[str] = mapped_column(Text, nullable=False)
    source_opportunity_ids: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    provider_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    business_context_state: Mapped[str] = mapped_column(Text, nullable=False, default="incomplete")
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    actual_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False, default=0)
    briefs_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    briefs_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    briefs_blocked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StrategyBrief(
    Base,
    WorkspaceScopedMixin,
    TimestampMixin,
    VersionMixin,
    ActorMixin,
    SoftDeleteMixin,
):
    __tablename__ = "strategy_briefs"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "structural_fingerprint", name="uq_strategy_briefs_workspace_fp"
        ),
        Index("ix_strategy_briefs_workspace_status", "workspace_id", "status"),
        Index("ix_strategy_briefs_workspace_run", "workspace_id", "strategy_run_id"),
        Index("ix_strategy_briefs_workspace_priority", "workspace_id", "priority"),
        Index("ix_strategy_briefs_workspace_objective", "workspace_id", "business_goal"),
        Index("ix_strategy_briefs_run", "strategy_run_id"),
        Index("ix_strategy_briefs_created_by", "created_by"),
        Index("ix_strategy_briefs_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    creative_angle: Mapped[str | None] = mapped_column(Text, nullable=True)
    core_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    hook_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_direction: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    success_metric: Mapped[str | None] = mapped_column(Text, nullable=True)
    commercial_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_complexity: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    risk_level: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    evidence_summary: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    priority: Mapped[str] = mapped_column(Text, nullable=False, default="watch")
    component_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score_reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    recommended_length: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_posting_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    required_assets: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    production_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    rights_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    compliance_requirements: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    estimated_provider_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    estimated_cost_range: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cost_state: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    capability_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_configured")
    business_context_state: Mapped[str] = mapped_column(Text, nullable=False, default="incomplete")
    performance_data_state: Mapped[str] = mapped_column(Text, nullable=False, default="no_data")
    structural_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    repetition_state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    repetition_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    audit_gate_status: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    writer_handoff_state: Mapped[str] = mapped_column(Text, nullable=False, default="blocked")
    created_by_worker: Mapped[str] = mapped_column(Text, nullable=False, default="strategist")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="draft")
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StrategyBriefOpportunity(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "strategy_brief_opportunities"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "strategy_brief_id",
            "opportunity_id",
            name="uq_strategy_brief_opportunity",
        ),
        Index(
            "ix_strategy_brief_opportunities_workspace_brief",
            "workspace_id",
            "strategy_brief_id",
        ),
        Index("ix_strategy_brief_opportunities_brief", "strategy_brief_id"),
        Index("ix_strategy_brief_opportunities_opportunity", "opportunity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="RESTRICT"),
        nullable=False,
    )


class StrategyAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "strategy_audits"
    __table_args__ = (
        Index(
            "ix_strategy_audits_workspace_brief_checked",
            "workspace_id",
            "strategy_brief_id",
            "checked_at",
        ),
        Index("ix_strategy_audits_workspace_run", "workspace_id", "strategy_run_id"),
        Index("ix_strategy_audits_brief", "strategy_brief_id"),
        Index("ix_strategy_audits_run", "strategy_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_brief_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_briefs.id", ondelete="CASCADE"),
        nullable=False,
    )
    strategy_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("strategy_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    evaluator_context_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="strategy-auditor-v1"
    )
    brief_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    blocked_reasons: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class StrategySchedule(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin, ActorMixin):
    __tablename__ = "strategy_schedules"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_strategy_schedule_workspace"),
        Index("ix_strategy_schedules_created_by", "created_by"),
        Index("ix_strategy_schedules_enabled_by", "enabled_by"),
        Index("ix_strategy_schedules_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    frequency: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    enabled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
