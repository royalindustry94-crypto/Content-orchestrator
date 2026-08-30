"""Provider-agnostic contracts for the Scout → Compliance pipeline.

Every pipeline stage talks to a ``PipelineProvider`` rather than to a vendor
SDK, so activating a live vendor later is an implementation swap behind these
dataclasses instead of an edit to the orchestration services.

Two implementations ship today: ``NullPipelineProvider`` (no provider, the
default, every stage stops truthfully at ``not_configured``) and
``SimulationPipelineProvider`` (deterministic, offline, zero-cost). Neither
reaches an external network. Records written by a provider always carry that
provider's ``state_label`` so stored output can never be mistaken for the
output of a different provider.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol, runtime_checkable

NOT_CONFIGURED = "not_configured"
SIMULATION = "simulation"


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a stage is executed without a configured provider.

    Services check ``PipelineProvider.is_configured`` before executing, so this
    is a guard against a caller skipping that check rather than a control-flow
    path. It must never be converted into a successful stage result.
    """


class ProviderExecutionError(RuntimeError):
    """Raised when a configured provider cannot produce a usable result.

    Stages record this as an explicit failure. There is deliberately no
    fallback to the not-configured path: a failed provider call is a failed
    run, not an unconfigured one.
    """


@dataclass(frozen=True)
class ProviderUsage:
    """Bounded accounting for the provider work behind one stage."""

    provider: str
    calls: int = 0
    tokens: int = 0
    cost_usd: Decimal = Decimal("0.00")


# --- Research (Scout) -------------------------------------------------------


@dataclass(frozen=True)
class SourceDraft:
    canonical_url: str
    source_type: str
    publisher: str | None
    author: str | None
    claim_supported: str | None
    freshness: str
    confidence: Decimal
    excerpt: str | None
    published_at: datetime | None = None


@dataclass(frozen=True)
class OpportunityDraft:
    title: str
    topic: str
    summary: str
    proposed_angle: str
    target_audience: str | None
    target_platform: str | None
    suggested_format: str | None
    freshness: str
    confidence: Decimal
    risk: str
    component_scores: dict[str, float] = field(default_factory=dict)
    score_reasoning: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchRequest:
    workspace_id: uuid.UUID
    objective: str
    permitted_sources: list[str]
    max_searches: int


@dataclass(frozen=True)
class ResearchResult:
    sources: list[SourceDraft]
    opportunity: OpportunityDraft
    usage: ProviderUsage


# --- Strategy ---------------------------------------------------------------


@dataclass(frozen=True)
class StrategyRequest:
    workspace_id: uuid.UUID
    objective: str
    opportunity_topics: list[str]
    opportunity_angles: list[str]
    opportunity_summaries: list[str]
    target_platform: str | None


@dataclass(frozen=True)
class StrategyBriefDraft:
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
    evidence_summary: str
    reasoning: str
    confidence: Decimal
    priority: str
    estimated_complexity: str
    risk_level: str
    recommended_length: str | None
    recommended_posting_window: str | None
    required_assets: list[str] = field(default_factory=list)
    production_requirements: list[str] = field(default_factory=list)
    rights_requirements: list[str] = field(default_factory=list)
    compliance_requirements: list[str] = field(default_factory=list)
    component_scores: dict[str, float] = field(default_factory=dict)
    score_reasoning: dict[str, str] = field(default_factory=dict)
    estimated_provider_usage: dict[str, int] = field(default_factory=dict)
    estimated_cost_range: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class StrategyResult:
    brief: StrategyBriefDraft
    usage: ProviderUsage


# --- Content Department -----------------------------------------------------


@dataclass(frozen=True)
class ContentRequest:
    workspace_id: uuid.UUID
    objective: str
    creative_angle: str | None
    core_message: str | None
    hook_direction: str | None
    cta_direction: str | None
    target_platform: str | None
    target_audience: str | None
    recommended_length: str | None


@dataclass(frozen=True)
class CreativeDirectionDraft:
    creative_concept: str
    opening_pattern: str
    story_structure: str
    tone: str
    pacing: str
    visual_direction: str
    audio_direction: str
    desired_emotion: str
    production_complexity: str
    estimated_duration: str
    required_claims: list[str] = field(default_factory=list)
    prohibited_claims: list[str] = field(default_factory=list)
    required_assets: list[str] = field(default_factory=list)
    risk_notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ScriptDraft:
    title: str
    description: str
    hook: str
    body: str
    cta: str


@dataclass(frozen=True)
class ContentResult:
    direction: CreativeDirectionDraft
    script: ScriptDraft
    usage: ProviderUsage


# --- Production (Producer) --------------------------------------------------


@dataclass(frozen=True)
class ProductionRequest:
    workspace_id: uuid.UUID
    script_hook: str
    script_body: str
    script_cta: str
    target_platform: str | None
    target_format: str | None
    target_duration_seconds: int | None


@dataclass(frozen=True)
class RenderedAssetDraft:
    asset_type: str
    model_version: str
    duration_seconds: Decimal | None
    dimensions: dict[str, int]
    generation_settings: dict[str, str]
    cost_usd: Decimal


@dataclass(frozen=True)
class ProductionResult:
    assets: list[RenderedAssetDraft]
    artifact_hash: str
    storage_reference: dict[str, object]
    duration_seconds: Decimal
    resolution: dict[str, int]
    aspect_ratio: str
    container: str
    codec: str
    usage: ProviderUsage


# --- Compliance -------------------------------------------------------------


@dataclass(frozen=True)
class ComplianceRequest:
    workspace_id: uuid.UUID
    target_platform: str
    artifact_hash: str
    script_hook: str
    script_body: str
    script_cta: str


@dataclass(frozen=True)
class ComplianceResult:
    risk_level: str
    reused_content_risk: str
    monetization_risk: str
    rights_status: str
    rights_basis: str
    findings: list[dict[str, str]] = field(default_factory=list)
    evidence: list[dict[str, str]] = field(default_factory=list)
    required_disclosures: list[str] = field(default_factory=list)
    policy_version: str = "unversioned"
    usage: ProviderUsage = ProviderUsage(provider=NOT_CONFIGURED)


@runtime_checkable
class PipelineProvider(Protocol):
    """The single seam between orchestration services and content vendors.

    Methods are async so an HTTP-backed vendor implementation can be dropped in
    without touching any call site, even though both providers shipped today
    are pure and perform no I/O.
    """

    name: str
    state_label: str
    is_configured: bool

    async def research(self, request: ResearchRequest) -> ResearchResult: ...

    async def strategy(self, request: StrategyRequest) -> StrategyResult: ...

    async def content(self, request: ContentRequest) -> ContentResult: ...

    async def production(self, request: ProductionRequest) -> ProductionResult: ...

    async def compliance(self, request: ComplianceRequest) -> ComplianceResult: ...
