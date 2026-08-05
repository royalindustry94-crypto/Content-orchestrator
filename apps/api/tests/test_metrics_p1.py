"""P-008 — /metrics Prometheus export smoke tests."""

from __future__ import annotations

import pytest

from app.core.config import get_settings


@pytest.mark.asyncio
async def test_metrics_endpoint_prometheus_format(client):
    res = await client.get("/metrics")
    assert res.status_code == 200, res.text
    body = res.text
    assert "co_up 1" in body
    assert "co_job_schedule_depth" in body
    assert "co_dead_letter_pending" in body
    assert "text/plain" in res.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_metrics_requires_bearer_when_token_configured(client, monkeypatch):
    monkeypatch.setenv("METRICS_SCRAPER_TOKEN", "scrape-secret-token")
    get_settings.cache_clear()
    try:
        denied = await client.get("/metrics")
        assert denied.status_code == 401
        bad = await client.get(
            "/metrics", headers={"Authorization": "Bearer wrong-token-xxxxx"}
        )
        assert bad.status_code == 401
        ok = await client.get(
            "/metrics", headers={"Authorization": "Bearer scrape-secret-token"}
        )
        assert ok.status_code == 200
        assert "co_up 1" in ok.text
    finally:
        monkeypatch.delenv("METRICS_SCRAPER_TOKEN", raising=False)
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_health_live_still_ok(client):
    res = await client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
