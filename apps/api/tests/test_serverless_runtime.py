"""RUNTIME_PROFILE=serverless: honest automation reporting and pooler safety.

The preview deployment (docs/ops/VERCEL_PREVIEW.md) runs the API as a Vercel
Function. A frozen-between-requests process cannot host the scheduler, outbox
relay or maintenance loops, so these tests pin two things:

1. the loops are not started, and /health/automation says so explicitly rather
   than reporting "idle", which would read as loops that should be ticking; and
2. the database engines are configured for a transaction-mode connection pooler.

They also pin that ``server`` (the default) is completely unchanged, so nothing
about container/uvicorn deployment shifted to enable preview hosting.
"""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from app import main as main_mod
from app.core.config import Settings
from app.db.session import connect_args_for, pool_kwargs_for
from app.main import app, automation_state
from app.serverless import PrefixStripMiddleware, strip_path_prefix

BASE_ENV = {
    "database_url": "postgresql://postgres:postgres@127.0.0.1:5432/co_test",
    "app_database_url": "postgresql://app_runtime:app_runtime@127.0.0.1:5432/co_test",
    "supabase_jwt_secret": "test-supabase-jwt-secret-0123456789abcdef",
}


def _settings(**overrides) -> Settings:
    return Settings(**{**BASE_ENV, **overrides})


# --- configuration -------------------------------------------------------


def test_runtime_profile_defaults_to_server() -> None:
    settings = _settings(environment="staging")
    assert settings.runtime_profile == "server"
    assert settings.is_serverless is False
    assert settings.background_loops_supported is True
    assert settings.background_loops_disabled_reason is None


def test_runtime_profile_rejects_unknown_value() -> None:
    with pytest.raises(ValueError, match="RUNTIME_PROFILE"):
        _settings(runtime_profile="lambda")


def test_runtime_profile_is_case_and_whitespace_normalized() -> None:
    assert _settings(runtime_profile=" SERVERLESS ").runtime_profile == "serverless"


def test_serverless_profile_disables_loops_with_a_reason() -> None:
    settings = _settings(environment="preview", runtime_profile="serverless")
    assert settings.is_serverless is True
    assert settings.background_loops_supported is False
    reason = settings.background_loops_disabled_reason
    assert reason is not None
    assert "serverless" in reason


def test_test_environment_reports_its_own_reason_not_the_serverless_one() -> None:
    settings = _settings(environment="test")
    assert settings.background_loops_supported is False
    assert "ENVIRONMENT=test" in (settings.background_loops_disabled_reason or "")


def test_simulation_provider_still_refused_in_production_under_serverless() -> None:
    """Preview hosting must not become a way to ship simulated output.

    ``auth_mode`` is pinned to supabase here only so the auth validator (which
    conftest's AUTH_MODE=local would otherwise trip first) does not mask the
    provider validator under test.
    """
    with pytest.raises(ValueError, match="simulation is forbidden"):
        _settings(
            environment="production",
            runtime_profile="serverless",
            auth_mode="supabase",
            pipeline_provider_mode="simulation",
        )


def test_local_auth_still_refused_in_production_under_serverless() -> None:
    with pytest.raises(ValueError, match="AUTH_MODE=local is forbidden"):
        _settings(environment="production", runtime_profile="serverless", auth_mode="local")


# --- database engine configuration ---------------------------------------


def test_server_profile_keeps_pooling_and_default_dbapi_args() -> None:
    assert pool_kwargs_for(is_test=False, is_serverless=False) == {"pool_pre_ping": True}
    assert connect_args_for(is_serverless=False) == {}


def test_serverless_profile_disables_pooling() -> None:
    from sqlalchemy.pool import NullPool

    assert pool_kwargs_for(is_test=False, is_serverless=True) == {"poolclass": NullPool}


def test_serverless_profile_is_safe_for_a_transaction_mode_pooler() -> None:
    args = connect_args_for(is_serverless=True)
    assert args["prepared_statement_cache_size"] == 0
    name_func = args["prepared_statement_name_func"]
    # Unique per call, or concurrent clients on a shared backend collide.
    assert name_func() != name_func()


# --- lifespan ------------------------------------------------------------


@pytest.mark.asyncio
async def test_lifespan_does_not_start_loops_under_serverless() -> None:
    previous_env = main_mod.settings.environment
    previous_profile = main_mod.settings.runtime_profile
    main_mod.settings.environment = "preview"
    main_mod.settings.runtime_profile = "serverless"
    automation_state.tasks_running = []
    try:
        async with main_mod.lifespan(main_mod.app):
            assert automation_state.tasks_running == []
            assert "serverless" in (automation_state.disabled_reason or "")
    finally:
        main_mod.settings.environment = previous_env
        main_mod.settings.runtime_profile = previous_profile
        automation_state.disabled_reason = None


# --- /health/automation --------------------------------------------------


@pytest.mark.asyncio
async def test_automation_health_reports_disabled_not_idle() -> None:
    """conftest pins ENVIRONMENT=test, so the loops are legitimately absent.

    The endpoint must name that fact instead of reporting "idle", which an
    operator would read as loops that are expected to be ticking but are not.
    """
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/automation")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "disabled"
    assert body["runtime_profile"] == "server"
    assert body["disabled_reason"]
    assert body["tasks_running"] == []
    # Loop-only work must be advertised as unavailable...
    assert "draft_desk_stage_dispatch" in body["unavailable_capabilities"]
    assert "outbox_catch_up_delivery" in body["unavailable_capabilities"]
    # ...while the request-inline pipeline is still advertised as working, which
    # is what makes the preview usable at all.
    inline = body["request_inline_capabilities"]
    assert "human_review_gate_open_and_decide" in inline
    assert "research_strategy_content_production_compliance_stages" in inline


# --- path prefix ---------------------------------------------------------


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api", "/"),
        ("/api/", "/"),
        ("/api/health/ready", "/health/ready"),
        ("/api/workspaces/123/review-gates", "/workspaces/123/review-gates"),
        # Already stripped upstream: must pass through untouched.
        ("/health/ready", "/health/ready"),
        # Must not corrupt a path that merely starts with the same letters.
        ("/apiary/things", "/apiary/things"),
    ],
)
def test_strip_path_prefix(path: str, expected: str) -> None:
    assert strip_path_prefix(path, "/api") == expected


@pytest.mark.asyncio
async def test_prefixed_requests_reach_the_real_routes() -> None:
    wrapped = PrefixStripMiddleware(app, "/api")
    transport = ASGITransport(app=wrapped)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        prefixed = await client.get("/api/health/live")
        provider = await client.get("/api/pipeline/provider")
        unprefixed = await client.get("/health/live")

    assert prefixed.status_code == 200
    assert prefixed.json() == {"status": "ok"}
    assert unprefixed.status_code == 200
    # The provider contract the web app reads for its banner must survive the
    # prefix rewrite, including the two invariants it advertises.
    assert provider.status_code == 200
    assert provider.json()["external_publishing_enabled"] is False
    assert provider.json()["human_review_required"] is True


@pytest.mark.asyncio
async def test_prefix_middleware_leaves_the_callers_scope_alone() -> None:
    """Mutating the caller's scope in place would corrupt any outer app."""
    seen: list[str] = []

    async def _inner(scope, receive, send):
        seen.append(scope["path"])

    scope = {"type": "http", "path": "/api/health/live", "raw_path": b"/api/health/live"}
    await PrefixStripMiddleware(_inner, "/api")(scope, None, None)

    assert seen == ["/health/live"]
    assert scope["path"] == "/api/health/live"
    assert scope["raw_path"] == b"/api/health/live"


@pytest.mark.asyncio
async def test_prefix_middleware_passes_lifespan_through_untouched() -> None:
    types: list[str] = []

    async def _inner(scope, receive, send):
        types.append(scope["type"])

    await PrefixStripMiddleware(_inner, "/api")({"type": "lifespan"}, None, None)
    assert types == ["lifespan"]
