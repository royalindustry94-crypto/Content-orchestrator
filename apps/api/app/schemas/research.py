"""Strict Scout and Research Auditor V1 API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    research_objective: str = Field(min_length=3, max_length=1000)
    permitted_sources: list[str] = Field(default_factory=list, max_length=25)
    max_searches: int = Field(default=5, ge=1, le=25)
    max_provider_calls: int = Field(default=5, ge=0, le=25)
    max_tokens: int = Field(default=4000, ge=0, le=100_000)
    max_cost_usd: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("25.00"))
    max_attempts: int = Field(default=3, ge=1, le=5)

    @field_validator("permitted_sources")
    @classmethod
    def source_list_is_bounded(cls, value: list[str]) -> list[str]:
        cleaned = []
        for item in value:
            normalized = item.strip()
            if not normalized or len(normalized) > 500:
                raise ValueError(
                    "permitted source entries must be non-empty and at most 500 characters"
                )
            cleaned.append(normalized)
        return cleaned


class ResearchRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    trigger: str
    research_objective: str
    permitted_sources: list[str]
    started_at: datetime
    deadline: datetime
    max_searches: int
    max_provider_calls: int
    max_tokens: int
    max_cost_usd: Decimal
    max_attempts: int
    status: str
    provider_state: str
    searches_used: int
    provider_calls_used: int
    tokens_used: int
    reserved_cost_usd: Decimal
    actual_cost_usd: Decimal
    opportunity_count: int
    audited_opportunity_count: int
    blocked_opportunity_count: int
    last_error: str | None
    correlation_id: uuid.UUID
    trace_id: str | None
    test_data: bool


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    canonical_url: str
    source_type: str
    retrieved_at: datetime
    published_at: datetime | None
    publisher: str | None
    author: str | None
    claim_supported: str | None
    freshness: str
    confidence: Decimal
    handling_state: str
    rejection_reason: str | None
    test_data: bool


class EvidenceOut(BaseModel):
    source: SourceOut
    claim_supported: str
    relevance: Decimal
    contradiction_flag: bool


class OpportunityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    research_run_id: uuid.UUID
    title: str
    topic: str
    summary: str
    proposed_angle: str
    target_audience: str | None
    target_platform: str | None
    suggested_format: str | None
    discovered_at: datetime
    freshness: str
    source_count: int
    confidence: Decimal
    risk: str
    status: str
    created_by_worker: str
    component_scores: dict
    score_reasoning: dict
    audit_gate_status: str
    performance_data_state: str
    strategist_state: str
    test_data: bool


class ResearchAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    opportunity_id: uuid.UUID
    research_run_id: uuid.UUID
    state: str
    evaluator_context_version: str
    findings: list[dict]
    warnings: list[str]
    blocked_reasons: list[str]
    checked_at: datetime
    test_data: bool


class OpportunityDetailOut(BaseModel):
    opportunity: OpportunityOut
    evidence: list[EvidenceOut]
    latest_audit: ResearchAuditOut | None


class ResearchSummaryOut(BaseModel):
    provider_state: str
    status: str
    current_research: ResearchRunOut | None
    last_run: ResearchRunOut | None
    next_run_at: datetime | None
    opportunities_found: int
    audited_opportunities: int
    blocked_findings: int
    cost_today_usd: Decimal
    last_error: str | None
    schedule_enabled: bool
    research_data_state: str


class StrategistGateOut(BaseModel):
    opportunity_id: uuid.UUID
    eligible: bool
    state: str
    detail: str
