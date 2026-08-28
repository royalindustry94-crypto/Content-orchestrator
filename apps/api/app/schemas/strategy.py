"""Strict Strategist and Strategy Auditor V1 API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrategyRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_objective: str = Field(min_length=3, max_length=1000)
    source_opportunity_ids: list[uuid.UUID] = Field(min_length=1, max_length=5)
    max_provider_calls: int = Field(default=5, ge=0, le=25)
    max_tokens: int = Field(default=4000, ge=0, le=100_000)
    max_cost_usd: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("25.00"))
    max_attempts: int = Field(default=3, ge=1, le=5)

    @field_validator("source_opportunity_ids")
    @classmethod
    def source_ids_are_unique(cls, value: list[uuid.UUID]) -> list[uuid.UUID]:
        if len(set(value)) != len(value):
            raise ValueError("source opportunity ids must be unique")
        return value


class StrategyRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    trigger: str
    strategy_objective: str
    source_opportunity_ids: list[str]
    started_at: datetime
    deadline: datetime
    max_provider_calls: int
    max_tokens: int
    max_cost_usd: Decimal
    max_attempts: int
    status: str
    provider_state: str
    business_context_state: str
    provider_calls_used: int
    tokens_used: int
    reserved_cost_usd: Decimal
    actual_cost_usd: Decimal
    briefs_created: int
    briefs_passed: int
    briefs_blocked: int
    last_error: str | None
    correlation_id: uuid.UUID
    trace_id: str | None
    test_data: bool


class StrategyBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    strategy_run_id: uuid.UUID
    objective: str
    target_audience: str | None
    target_platform: str | None
    content_format: str | None
    creative_angle: str | None
    core_message: str | None
    hook_direction: str | None
    cta_direction: str | None
    business_goal: str | None
    success_metric: str | None
    commercial_goal: str | None
    estimated_complexity: str
    risk_level: str
    evidence_summary: str
    reasoning: str
    confidence: Decimal
    priority: str
    component_scores: dict
    score_reasoning: dict
    recommended_length: str | None
    recommended_posting_window: str | None
    required_assets: list[str]
    production_requirements: list[str]
    rights_requirements: list[str]
    compliance_requirements: list[str]
    estimated_provider_usage: dict
    estimated_cost_range: dict
    cost_state: str
    capability_state: str
    business_context_state: str
    performance_data_state: str
    structural_fingerprint: str
    repetition_state: str
    repetition_reasons: list[str]
    audit_gate_status: str
    writer_handoff_state: str
    created_by_worker: str
    status: str
    test_data: bool


class StrategyAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    strategy_brief_id: uuid.UUID
    strategy_run_id: uuid.UUID
    state: str
    evaluator_context_version: str
    findings: list[dict]
    warnings: list[str]
    blocked_reasons: list[str]
    checked_at: datetime
    test_data: bool


class StrategyBriefDetailOut(BaseModel):
    brief: StrategyBriefOut
    source_opportunity_ids: list[uuid.UUID]
    latest_audit: StrategyAuditOut | None


class StrategySummaryOut(BaseModel):
    provider_state: str
    status: str
    current_strategy: StrategyRunOut | None
    last_run: StrategyRunOut | None
    next_run_at: datetime | None
    opportunities_received: int
    briefs_created: int
    briefs_passed: int
    briefs_blocked: int
    cost_today_usd: Decimal
    last_error: str | None
    schedule_enabled: bool
    business_context_state: str
    performance_data_state: str


class WriterGateOut(BaseModel):
    strategy_brief_id: uuid.UUID
    eligible: bool
    state: str
    detail: str
