"""Mission Control V4 integrated search, timeline, logs, executive, assistant."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_mission_control_v4_integrated_modules(client, new_user):
    _user_id, _token, headers = new_user
    workspace = await client.post(
        "/workspaces", headers=headers, json={"name": "V4 Mission Control"}
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    content = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Searchable launch video", "script_body": "Live script"},
    )
    assert content.status_code == 201, content.text
    run_id = content.json()["pipeline_run_id"]

    lead = await client.post(
        f"/workspaces/{workspace_id}/operations/leads",
        headers=headers,
        json={
            "name": "Searchable Founder",
            "email": "searchable@example.com",
            "company": "Search Labs",
            "source": "inbound",
        },
    )
    assert lead.status_code == 201

    provisioned = await client.post(
        f"/workspaces/{workspace_id}/workers",
        headers=headers,
        json={
            "name": "searchable-worker-4",
            "supported_stages": ["scripting"],
            "max_concurrency": 2,
        },
    )
    assert provisioned.status_code == 201, provisioned.text
    worker = provisioned.json()
    worker_headers = {
        "Authorization": f"Bearer {worker['worker_secret']}"
    }

    log = await client.post(
        "/workers/logs",
        headers=worker_headers,
        json={
            "severity": "error",
            "message": "Provider timeout while rendering searchable video",
            "pipeline_run_id": run_id,
            "occurred_at": datetime.now(UTC).isoformat(),
            "context": {"provider": "video-provider"},
        },
    )
    assert log.status_code == 202, log.text

    search = await client.get(
        f"/workspaces/{workspace_id}/operations/search",
        headers=headers,
        params={"q": "searchable"},
    )
    assert search.status_code == 200, search.text
    types = {result["type"] for result in search.json()["results"]}
    assert {"lead", "worker", "content"} <= types

    customer_search = await client.get(
        f"/workspaces/{workspace_id}/operations/search",
        headers=headers,
        params={"q": "V4 Mission"},
    )
    assert customer_search.status_code == 200
    assert any(
        row["type"] == "customer"
        for row in customer_search.json()["results"]
    )

    log_search = await client.get(
        f"/workspaces/{workspace_id}/operations/search",
        headers=headers,
        params={"q": "Provider timeout"},
    )
    assert log_search.status_code == 200
    assert any(row["type"] == "log" for row in log_search.json()["results"])

    logs = await client.get(
        f"/workspaces/{workspace_id}/operations/logs",
        headers=headers,
        params={"worker_id": worker["worker_id"], "severity": "error"},
    )
    assert logs.status_code == 200
    assert logs.json()["logs"][0]["message"].startswith("Provider timeout")

    timeline = await client.get(
        f"/workspaces/{workspace_id}/operations/timeline", headers=headers
    )
    assert timeline.status_code == 200
    assert any(
        item["source"] == "worker_logs" for item in timeline.json()["items"]
    )

    executive = await client.get(
        f"/workspaces/{workspace_id}/operations/executive-mode",
        headers=headers,
    )
    assert executive.status_code == 200, executive.text
    body = executive.json()
    assert len(body["health"]) == 7
    assert "revenue_mtd_usd" in body
    assert "reviews_waiting" in body
    assert body["todays_summary"]

    for question, intent in (
        ("What failed today?", "failures_today"),
        ("Why is worker searchable-worker-4 idle?", "worker_idle"),
        ("Show today's spend.", "spend"),
        ("Show blocked reviews.", "blocked_reviews"),
        ("Show failed pipelines.", "failed_pipelines"),
    ):
        answer = await client.post(
            f"/workspaces/{workspace_id}/operations/assistant",
            headers=headers,
            json={"question": question},
        )
        assert answer.status_code == 200, answer.text
        assert answer.json()["intent"] == intent
        assert answer.json()["answer"]


@pytest.mark.asyncio
async def test_worker_log_ingest_rejects_foreign_references_and_oversized_context(
    client, new_user
):
    _user_id, _token, headers = new_user
    workspace_a = (
        await client.post("/workspaces", headers=headers, json={"name": "Logs tenant A"})
    ).json()["id"]
    workspace_b = (
        await client.post("/workspaces", headers=headers, json={"name": "Logs tenant B"})
    ).json()["id"]
    content_b = await client.post(
        f"/workspaces/{workspace_b}/content-jobs",
        headers=headers,
        json={"topic": "Foreign pipeline", "script_body": "Private"},
    )
    assert content_b.status_code == 201
    pipeline_b = content_b.json()["pipeline_run_id"]

    worker_a = (
        await client.post(
            f"/workspaces/{workspace_a}/workers",
            headers=headers,
            json={"name": "logs-worker-a", "supported_stages": ["scripting"]},
        )
    ).json()
    worker_b = (
        await client.post(
            f"/workspaces/{workspace_b}/workers",
            headers=headers,
            json={"name": "logs-worker-b", "supported_stages": ["scripting"]},
        )
    ).json()
    assignment_b = uuid.uuid4()
    now = datetime.now(UTC)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO stage_assignments (
                    id, workspace_id, pipeline_run_id, stage, attempt_number,
                    worker_id, status, idempotency_key, lease_expires_at,
                    dispatched_at, priority
                ) VALUES (
                    :id, :workspace_id, :pipeline_run_id,
                    'scripting'::content_stage, 1, :worker_id,
                    'acknowledged'::stage_assignment_status, :idempotency_key,
                    :lease_expires_at, :dispatched_at, 0
                )
                """
            ),
            {
                "id": str(assignment_b),
                "workspace_id": workspace_b,
                "pipeline_run_id": pipeline_b,
                "worker_id": worker_b["worker_id"],
                "idempotency_key": f"foreign-log-{assignment_b}",
                "lease_expires_at": now + timedelta(minutes=5),
                "dispatched_at": now,
            },
        )
        await session.commit()

    worker_a_headers = {"Authorization": f"Bearer {worker_a['worker_secret']}"}
    unauthenticated = await client.post(
        "/workers/logs",
        json={"severity": "info", "message": "must authenticate"},
    )
    assert unauthenticated.status_code == 401

    foreign_pipeline = await client.post(
        "/workers/logs",
        headers=worker_a_headers,
        json={
            "severity": "warning",
            "message": "foreign pipeline reference",
            "pipeline_run_id": pipeline_b,
        },
    )
    assert foreign_pipeline.status_code == 422

    foreign_assignment = await client.post(
        "/workers/logs",
        headers=worker_a_headers,
        json={
            "severity": "warning",
            "message": "foreign assignment reference",
            "assignment_id": str(assignment_b),
        },
    )
    assert foreign_assignment.status_code == 422

    oversized_context = await client.post(
        "/workers/logs",
        headers=worker_a_headers,
        json={
            "severity": "info",
            "message": "oversized context",
            "context": {"payload": "x" * (16 * 1024)},
        },
    )
    assert oversized_context.status_code == 422


@pytest.mark.asyncio
async def test_v4_endpoints_require_admin(client, new_user):
    _owner_id, _token, owner_headers = new_user
    workspace = await client.post(
        "/workspaces", headers=owner_headers, json={"name": "Private V4"}
    )
    workspace_id = workspace.json()["id"]
    outsider = await client.post(
        "/auth/signup",
        json={
            "email": f"{uuid.uuid4()}@example.com",
            "password": "securepass1-beta",
        },
    )
    outsider_headers = {
        "Authorization": f"Bearer {outsider.json()['access_token']}"
    }
    for endpoint in ("search?q=private", "timeline", "logs", "executive-mode"):
        response = await client.get(
            f"/workspaces/{workspace_id}/operations/{endpoint}",
            headers=outsider_headers,
        )
        assert response.status_code == 403

    assistant = await client.post(
        f"/workspaces/{workspace_id}/operations/assistant",
        headers=outsider_headers,
        json={"question": "Show private spend"},
    )
    assert assistant.status_code == 403
