"""Bounded, evidence-backed Scout and independent Research Auditor records."""

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


class ResearchRun(Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin, ActorMixin):
    __tablename__ = "research_runs"
    __table_args__ = (
        Index("ix_research_runs_workspace_created", "workspace_id", "created_at"),
        Index("ix_research_runs_workspace_status", "workspace_id", "status"),
        Index(
            "ix_research_runs_workspace_correlation", "workspace_id", "correlation_id"
        ),
        Index("ix_research_runs_created_by", "created_by"),
        Index("ix_research_runs_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    trigger: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    research_objective: Mapped[str] = mapped_column(Text, nullable=False)
    permitted_sources: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    max_searches: Mapped[int] = mapped_column(Integer, nullable=False)
    max_provider_calls: Mapped[int] = mapped_column(Integer, nullable=False)
    max_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    max_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default="queued")
    provider_state: Mapped[str] = mapped_column(
        Text, nullable=False, default="not_configured"
    )
    searches_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_calls_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reserved_cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False, default=0
    )
    actual_cost_usd: Mapped[float] = mapped_column(
        Numeric(10, 4), nullable=False, default=0
    )
    opportunity_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audited_opportunity_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    blocked_opportunity_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, default=uuid.uuid4
    )
    trace_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ResearchSource(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "research_sources"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "research_run_id",
            "canonical_url",
            name="uq_research_source_run_url",
        ),
        Index("ix_research_sources_workspace_run", "workspace_id", "research_run_id"),
        Index("ix_research_sources_workspace_digest", "workspace_id", "content_digest"),
        Index("ix_research_sources_run", "research_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    publisher: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(Text, nullable=True)
    claim_supported: Mapped[str | None] = mapped_column(Text, nullable=True)
    freshness: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    content_digest: Mapped[str] = mapped_column(Text, nullable=False)
    safe_excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    handling_state: Mapped[str] = mapped_column(
        Text, nullable=False, default="accepted"
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Opportunity(
    Base,
    WorkspaceScopedMixin,
    TimestampMixin,
    VersionMixin,
    ActorMixin,
    SoftDeleteMixin,
):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id", "dedupe_key", name="uq_opportunities_workspace_dedupe"
        ),
        Index("ix_opportunities_workspace_status", "workspace_id", "status"),
        Index("ix_opportunities_workspace_run", "workspace_id", "research_run_id"),
        Index("ix_opportunities_workspace_topic", "workspace_id", "topic"),
        Index("ix_opportunities_run", "research_run_id"),
        Index("ix_opportunities_created_by", "created_by"),
        Index("ix_opportunities_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_angle: Mapped[str] = mapped_column(Text, nullable=False)
    target_audience: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_platform: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_format: Mapped[str | None] = mapped_column(Text, nullable=True)
    discovered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    freshness: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    risk: Mapped[str] = mapped_column(Text, nullable=False, default="unknown")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="watching")
    created_by_worker: Mapped[str] = mapped_column(
        Text, nullable=False, default="scout"
    )
    component_scores: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    score_reasoning: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    dedupe_key: Mapped[str] = mapped_column(Text, nullable=False)
    audit_gate_status: Mapped[str] = mapped_column(
        Text, nullable=False, default="not_run"
    )
    performance_data_state: Mapped[str] = mapped_column(
        Text, nullable=False, default="no_performance_data"
    )
    strategist_state: Mapped[str] = mapped_column(
        Text, nullable=False, default="not_sent"
    )
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class OpportunityEvidence(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "opportunity_evidence"
    __table_args__ = (
        UniqueConstraint(
            "workspace_id",
            "opportunity_id",
            "source_id",
            name="uq_opportunity_evidence_link",
        ),
        Index(
            "ix_opportunity_evidence_workspace_opportunity",
            "workspace_id",
            "opportunity_id",
        ),
        Index("ix_opportunity_evidence_opportunity", "opportunity_id"),
        Index("ix_opportunity_evidence_source", "source_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_sources.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_supported: Mapped[str] = mapped_column(Text, nullable=False)
    relevance: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0)
    contradiction_flag: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )


class ResearchAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "research_audits"
    __table_args__ = (
        Index(
            "ix_research_audits_workspace_opportunity_checked",
            "workspace_id",
            "opportunity_id",
            "checked_at",
        ),
        Index("ix_research_audits_workspace_run", "workspace_id", "research_run_id"),
        Index("ix_research_audits_opportunity", "opportunity_id"),
        Index("ix_research_audits_run", "research_run_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    opportunity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("opportunities.id", ondelete="CASCADE"),
        nullable=False,
    )
    research_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("research_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="not_run")
    evaluator_context_version: Mapped[str] = mapped_column(
        Text, nullable=False, default="research-auditor-v1"
    )
    scout_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list[dict]] = mapped_column(JSONB, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    blocked_reasons: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    test_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ResearchSchedule(
    Base, WorkspaceScopedMixin, TimestampMixin, VersionMixin, ActorMixin
):
    __tablename__ = "research_schedules"
    __table_args__ = (
        UniqueConstraint("workspace_id", name="uq_research_schedule_workspace"),
        Index("ix_research_schedules_created_by", "created_by"),
        Index("ix_research_schedules_enabled_by", "enabled_by"),
        Index("ix_research_schedules_updated_by", "updated_by"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    frequency: Mapped[str] = mapped_column(Text, nullable=False, default="manual")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_run_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    enabled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True
    )
