"""Strict Content Department V1 API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AuditType = Literal["language", "fact", "brand", "originality"]
AuditState = Literal["not_run", "pass", "pass_with_warning", "blocked", "error"]


class ContentDepartmentRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_brief_id: uuid.UUID
    # Set when this run revises an earlier package. The prior package is
    # superseded and its audits are invalidated, so a revision can never
    # inherit approval granted to different words.
    prior_content_package_id: uuid.UUID | None = None
    max_provider_calls: int = Field(default=5, ge=0, le=25)
    max_tokens: int = Field(default=4000, ge=0, le=100_000)
    max_cost_usd: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("25.00"))
    max_attempts: int = Field(default=3, ge=1, le=5)
    timeout_seconds: int = Field(default=900, ge=30, le=3600)


class ContentDepartmentRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    strategy_brief_id: uuid.UUID
    trigger: str
    status: str
    provider_state: str
    business_context_state: str
    max_provider_calls: int
    max_tokens: int
    max_cost_usd: Decimal
    max_attempts: int
    timeout_seconds: int
    provider_calls_used: int
    tokens_used: int
    actual_cost_usd: Decimal
    creative_directions_created: int
    packages_ready: int
    packages_blocked: int
    last_error: str | None
    correlation_id: uuid.UUID
    trace_id: str | None
    test_data: bool


class CreativeDirectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_department_run_id: uuid.UUID
    strategy_brief_id: uuid.UUID
    objective: str
    target_platform: str | None
    target_audience: str | None
    creative_concept: str
    opening_pattern: str | None
    hook_direction: str | None
    story_structure: str | None
    tone: str | None
    pacing: str | None
    visual_direction: str | None
    audio_direction: str | None
    cta_direction: str | None
    desired_emotion: str | None
    required_claims: list
    prohibited_claims: list
    required_assets: list
    estimated_duration: str | None
    production_complexity: str
    risk_notes: list
    worker_id: str
    provider: str
    model: str | None
    prompt_version: str
    status: str
    test_data: bool


class ContentPackageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_department_run_id: uuid.UUID
    creative_direction_id: uuid.UUID
    strategy_brief_id: uuid.UUID
    content_item_id: uuid.UUID
    content_version_id: uuid.UUID
    prior_content_version_id: uuid.UUID | None
    revision_reason: str | None
    writer_worker_id: str
    provider: str
    model: str | None
    prompt_version: str
    input_references: dict
    package_fields: dict
    status: str
    audit_gate_status: str
    producer_handoff_state: str
    invalidated_at: datetime | None
    test_data: bool
    # Carried on the list item so a package card can report the originality
    # result directly instead of inferring it from the aggregate gate, which
    # cannot distinguish which auditor blocked.
    originality_state: str = "not_run"


class ContentClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_package_id: uuid.UUID
    content_version_id: uuid.UUID
    claim_text: str
    claim_type: str
    source_required: bool
    supporting_evidence: list
    verification_status: str
    confidence: Decimal
    risk: str
    freshness: str | None
    evidence_reasoning: str | None
    test_data: bool


class ContentAuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_package_id: uuid.UUID
    content_version_id: uuid.UUID
    auditor_type: AuditType
    auditor_worker_id: str
    state: AuditState
    artifact_snapshot: dict
    requirements_snapshot: dict
    findings: list
    warnings: list
    blocked_reasons: list
    evidence: list
    checked_at: datetime
    cost_usd: Decimal
    retry_history: list
    test_data: bool


class OriginalityFingerprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    content_package_id: uuid.UUID
    content_version_id: uuid.UUID
    text_fingerprint: str
    hook_fingerprint: str
    structure_fingerprint: str
    semantic_reference: str | None
    comparison_set: list
    similarity_findings: list
    state: str
    test_data: bool


class ContentPackageDetailOut(BaseModel):
    package: ContentPackageOut
    direction: CreativeDirectionOut
    claims: list[ContentClaimOut]
    audits: list[ContentAuditOut]
    originality: OriginalityFingerprintOut | None
    invalidation_count: int


class ContentDepartmentSummaryOut(BaseModel):
    provider_state: str
    status: str
    current_run: ContentDepartmentRunOut | None
    last_run: ContentDepartmentRunOut | None
    creative_directions: int
    packages_ready: int
    packages_blocked: int
    packages_in_progress: int
    claims_unverified: int
    cost_today_usd: Decimal
    last_error: str | None
    schedule_enabled: bool
    business_context_state: str
    performance_data_state: str


class ProducerGateOut(BaseModel):
    content_package_id: uuid.UUID
    eligible: bool
    state: str
    detail: str
