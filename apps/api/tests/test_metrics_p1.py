"""P-008 — /metrics Prometheus export smoke tests."""

from __future__ import annotations

import pytest


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
async def test_health_live_still_ok(client):
    res = await client.get("/health/live")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"
