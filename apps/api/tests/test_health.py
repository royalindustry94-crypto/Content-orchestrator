"""Health endpoint tests.

Environment variables are forced by conftest.py before this module is
imported, so no setdefault calls are needed here.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import httpx
import pytest
from httpx import ASGITransport

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_liveness_returns_ok() -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readiness_returns_200_when_db_reachable() -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_readiness_returns_503_when_db_unreachable() -> None:
    """The readiness endpoint must return 503 (not raise an unhandled
    exception) when the database is unreachable. We simulate the failure
    by overriding the ``get_db`` dependency to yield a mock session whose
    ``execute`` method always raises.
    """
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=RuntimeError("simulated: DB unreachable"))

    async def _broken_db():
        yield mock_session

    app.dependency_overrides[get_db] = _broken_db
    try:
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health/ready")
        assert response.status_code == 503
    finally:
        del app.dependency_overrides[get_db]
