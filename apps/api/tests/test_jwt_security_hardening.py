"""Regression tests for P0-1 (2026-09-13 independent audit): JWT secret
strength/placeholder validation, issuer checking, and UUID `sub` enforcement.
"""

from __future__ import annotations

import time

import pytest
from jwt import encode as jwt_encode
from pydantic import ValidationError

from app.core import security as security_module
from app.core.config import Settings
from tests.conftest import make_token


def _base_settings_kwargs(**overrides) -> dict:
    kwargs = {
        "database_url": "postgresql://postgres:postgres@127.0.0.1:5432/content_orchestrator_test",
        "app_database_url": (
            "postgresql://app_runtime:rotated-test-password@127.0.0.1:5432/content_orchestrator_test"
        ),
        "supabase_jwt_secret": "test-supabase-jwt-secret-0123456789abcdef",
        "environment": "development",
        "auth_mode": "supabase",
    }
    kwargs.update(overrides)
    return kwargs


# --- Settings: SUPABASE_JWT_SECRET strength/placeholder validation ---


def test_blank_secret_rejected_outside_test():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(**_base_settings_kwargs(supabase_jwt_secret=""))


def test_short_secret_rejected_outside_test():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(**_base_settings_kwargs(supabase_jwt_secret="too-short"))


@pytest.mark.parametrize(
    "weak_secret",
    [
        "secret",
        "changeme",
        "password",
        # Long enough to pass the length check alone — must still be
        # rejected by name, not just by length.
        "super-secret-jwt-token-with-at-least-32-characters-long",
        "SUPER-SECRET-JWT-TOKEN-WITH-AT-LEAST-32-CHARACTERS-LONG",
    ],
)
def test_known_placeholder_secret_rejected(weak_secret: str):
    with pytest.raises(ValidationError, match="placeholder|32 bytes"):
        Settings(**_base_settings_kwargs(supabase_jwt_secret=weak_secret))


def test_predictable_low_entropy_secret_rejected():
    with pytest.raises(ValidationError, match="predictable"):
        Settings(**_base_settings_kwargs(supabase_jwt_secret="a" * 40))


def test_real_random_secret_accepted():
    settings = Settings(**_base_settings_kwargs())
    assert settings.environment == "development"


def test_weak_secret_exempt_under_environment_test():
    """tests/conftest.py itself relies on this exemption (its fixed
    41-byte string is fine, but a short/blank secret under
    ENVIRONMENT=test must not start failing this validator either)."""
    settings = Settings(**_base_settings_kwargs(environment="test", supabase_jwt_secret="x"))
    assert settings.environment == "test"


def test_production_also_enforces_secret_strength():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(**_base_settings_kwargs(environment="production", supabase_jwt_secret="short"))


# --- security.get_current_user: UUID `sub` enforcement ---


@pytest.mark.asyncio
async def test_non_uuid_sub_is_rejected(client):
    token = make_token(user_id="not-a-uuid")
    response = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
    assert "sub" in response.json()["detail"]


@pytest.mark.asyncio
async def test_valid_uuid_sub_is_accepted(client):
    token = make_token()
    response = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# --- security._decode_supabase_jwt: optional issuer enforcement ---


@pytest.mark.asyncio
async def test_issuer_mismatch_rejected_when_configured(client, monkeypatch):
    # Patch the actual object app.core.security decodes against — not a
    # fresh get_settings() call, which some other test modules' own
    # get_settings.cache_clear() usage can make return a different
    # instance than the one security.py captured at import time.
    monkeypatch.setattr(
        security_module.settings, "supabase_jwt_issuer", "https://expected.example/auth/v1"
    )
    token = make_token()  # conftest's make_token never sets an `iss` claim
    response = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_issuer_match_accepted_when_configured(client, monkeypatch):
    settings = security_module.settings
    monkeypatch.setattr(settings, "supabase_jwt_issuer", "https://expected.example/auth/v1")
    payload = {
        "sub": "11111111-1111-1111-1111-111111111111",
        "email": "test@example.com",
        "aud": settings.supabase_jwt_audience,
        "exp": int(time.time()) + 3600,
        "role": "authenticated",
        "iss": "https://expected.example/auth/v1",
    }
    token = jwt_encode(
        payload, settings.supabase_jwt_secret, algorithm=settings.supabase_jwt_algorithm
    )
    response = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_issuer_not_required_when_unconfigured(client):
    """Default behavior (SUPABASE_JWT_ISSUER unset) is unchanged: a token
    with no `iss` claim at all is still accepted."""
    token = make_token()
    response = await client.get("/workspaces", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
