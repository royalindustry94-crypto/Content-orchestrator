"""Provider selection, configuration guards, and default fail-closed behaviour."""

from __future__ import annotations

import uuid

import pytest

from app.core.config import Settings, get_settings
from app.providers import (
    NullPipelineProvider,
    ProviderNotConfiguredError,
    ResearchRequest,
    SimulationPipelineProvider,
    get_pipeline_provider,
    provider_status,
)


def _settings(**overrides) -> Settings:
    base = {
        "DATABASE_URL": "postgresql://postgres:postgres@127.0.0.1:5432/x",
        "APP_DATABASE_URL": "postgresql://app_runtime:app_runtime@127.0.0.1:5432/x",
        "SUPABASE_JWT_SECRET": "secret-value-0123456789abcdef",
        # Pinned so a production case fails on the provider rule under test
        # rather than on the unrelated AUTH_MODE=local production rule.
        "AUTH_MODE": "supabase",
    }
    base.update(overrides)
    return Settings(**{key.lower(): value for key, value in base.items()})


def test_default_provider_mode_is_null():
    assert _settings().pipeline_provider_mode == "null"


def test_simulation_is_refused_in_production():
    # Simulated content is synthetic by construction, so unlike AUTH_MODE=local
    # there is deliberately no break-glass override for this one.
    message = "PIPELINE_PROVIDER_MODE=simulation is forbidden"
    with pytest.raises(ValueError, match=message):
        _settings(ENVIRONMENT="production", PIPELINE_PROVIDER_MODE="simulation")
    with pytest.raises(ValueError, match=message):
        _settings(ENVIRONMENT="prod", PIPELINE_PROVIDER_MODE="simulation")


def test_null_provider_is_allowed_in_production():
    assert _settings(ENVIRONMENT="production").pipeline_provider_mode == "null"


def test_unknown_provider_mode_is_rejected():
    with pytest.raises(ValueError, match="PIPELINE_PROVIDER_MODE must be"):
        _settings(PIPELINE_PROVIDER_MODE="openai")


def test_provider_mode_is_normalised():
    assert _settings(PIPELINE_PROVIDER_MODE="SIMULATION").pipeline_provider_mode == "simulation"


async def test_null_provider_refuses_every_stage():
    provider = NullPipelineProvider()
    assert provider.is_configured is False
    with pytest.raises(ProviderNotConfiguredError):
        await provider.research(
            ResearchRequest(
                workspace_id=uuid.uuid4(), objective="x", permitted_sources=[], max_searches=1
            )
        )


async def test_simulation_provider_is_deterministic():
    provider = SimulationPipelineProvider()
    workspace_id = uuid.uuid4()
    request = ResearchRequest(
        workspace_id=workspace_id,
        objective="A repeatable objective",
        permitted_sources=[],
        max_searches=5,
    )
    first = await provider.research(request)
    second = await provider.research(request)
    assert first == second


async def test_simulation_provider_varies_with_the_request():
    provider = SimulationPipelineProvider()
    workspace_id = uuid.uuid4()

    def request(objective: str) -> ResearchRequest:
        return ResearchRequest(
            workspace_id=workspace_id,
            objective=objective,
            permitted_sources=[],
            max_searches=5,
        )

    first = await provider.research(request("Short form retention"))
    second = await provider.research(request("Cold outreach sequencing"))
    assert first.opportunity.topic != second.opportunity.topic


async def test_simulation_provider_spends_nothing():
    provider = SimulationPipelineProvider()
    result = await provider.research(
        ResearchRequest(
            workspace_id=uuid.uuid4(), objective="Cost check", permitted_sources=[], max_searches=3
        )
    )
    assert result.usage.cost_usd == 0
    assert result.usage.calls == 0


def test_registry_returns_the_configured_provider(monkeypatch):
    assert get_pipeline_provider().is_configured is False

    monkeypatch.setenv("PIPELINE_PROVIDER_MODE", "simulation")
    get_settings.cache_clear()
    get_pipeline_provider.cache_clear()
    try:
        assert get_pipeline_provider().name == "simulation"
        status = provider_status()
        assert status["simulated"] is True
        # These two hold in every mode; the UI relies on them to stay honest.
        assert status["external_publishing_enabled"] is False
        assert status["human_review_required"] is True
    finally:
        monkeypatch.delenv("PIPELINE_PROVIDER_MODE", raising=False)
        get_settings.cache_clear()
        get_pipeline_provider.cache_clear()


async def test_provider_endpoint_reports_the_default_mode(client):
    response = await client.get("/pipeline/provider")
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "null"
    assert body["configured"] is False
    assert body["simulated"] is False


async def test_pipeline_stages_stay_fail_closed_without_a_provider(client, new_user):
    """The default deployment must behave exactly as it did before this seam."""
    _, _, headers = new_user
    workspace = await client.post("/workspaces", json={"name": "null-mode"}, headers=headers)
    workspace_id = workspace.json()["id"]

    run = await client.post(
        f"/workspaces/{workspace_id}/research/runs",
        json={"research_objective": "Nothing should execute"},
        headers=headers,
    )
    assert run.status_code == 201
    assert run.json()["status"] == "provider_not_configured"
    assert run.json()["provider_state"] == "not_configured"

    opportunities = await client.get(
        f"/workspaces/{workspace_id}/research/opportunities", headers=headers
    )
    assert opportunities.json() == []
