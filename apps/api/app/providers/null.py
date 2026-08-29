"""The default provider: no content vendor is configured.

Every method raises. Services must consult ``is_configured`` first and persist
their truthful ``provider_not_configured`` state instead of calling through,
so reaching one of these methods means a caller skipped that check.
"""

from __future__ import annotations

from app.providers.base import (
    NOT_CONFIGURED,
    ComplianceRequest,
    ComplianceResult,
    ContentRequest,
    ContentResult,
    ProductionRequest,
    ProductionResult,
    ProviderNotConfiguredError,
    ResearchRequest,
    ResearchResult,
    StrategyRequest,
    StrategyResult,
)


class NullPipelineProvider:
    """Fail-closed provider used whenever no vendor has been activated."""

    name = "none"
    state_label = NOT_CONFIGURED
    is_configured = False

    def _refuse(self, stage: str) -> ProviderNotConfiguredError:
        return ProviderNotConfiguredError(
            f"no {stage} provider is configured; "
            "set PIPELINE_PROVIDER_MODE to a configured provider to execute this stage"
        )

    async def research(self, request: ResearchRequest) -> ResearchResult:
        raise self._refuse("research")

    async def strategy(self, request: StrategyRequest) -> StrategyResult:
        raise self._refuse("strategy")

    async def content(self, request: ContentRequest) -> ContentResult:
        raise self._refuse("content")

    async def production(self, request: ProductionRequest) -> ProductionResult:
        raise self._refuse("production")

    async def compliance(self, request: ComplianceRequest) -> ComplianceResult:
        raise self._refuse("compliance")
