"""P-005 — OpenAPI / docs disabled outside development."""

from __future__ import annotations

import pytest

from app.core.config import openapi_route_kwargs


@pytest.mark.parametrize(
    ("environment", "enabled"),
    [
        ("development", True),
        ("dev", True),
        ("Development", True),
        ("test", False),
        ("staging", False),
        ("production", False),
        ("prod", False),
    ],
)
def test_openapi_route_kwargs_by_environment(environment: str, enabled: bool):
    kwargs = openapi_route_kwargs(environment)
    if enabled:
        assert kwargs == {
            "docs_url": "/docs",
            "redoc_url": "/redoc",
            "openapi_url": "/openapi.json",
        }
    else:
        assert kwargs == {
            "docs_url": None,
            "redoc_url": None,
            "openapi_url": None,
        }


@pytest.mark.asyncio
async def test_openapi_and_docs_unavailable_in_test_env(client):
    # conftest sets ENVIRONMENT=test before app import → docs disabled.
    for path in ("/openapi.json", "/docs", "/redoc"):
        res = await client.get(path)
        assert res.status_code == 404, path
