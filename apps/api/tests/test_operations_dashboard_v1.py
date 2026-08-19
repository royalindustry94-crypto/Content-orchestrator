"""Operations Dashboard V1: real projections, auth, and alert coverage."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_operations_dashboard_real_data(client, new_user, monkeypatch):
    user_id, _token, headers = new_user
    workspace = await client.post(
        "/workspaces", headers=headers, json={"name": "Lumora Operations"}
    )
    assert workspace.status_code == 201
    workspace_id = workspace.json()["id"]

    draft = await client.post(
        f"/workspaces/{workspace_id}/content-jobs",
        headers=headers,
        json={"topic": "Operations signal", "script_body": "Real draft"},
    )
    assert draft.status_code == 201, draft.text
    run_id = draft.json()["pipeline_run_id"]
    worker_id = uuid.uuid4()
    assignment_id = uuid.uuid4()
    job_id = uuid.uuid4()
    now = datetime.now(UTC)

    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                """
                INSERT INTO worker_registry (
                    id, workspace_id, name, supported_stages, status,
                    max_concurrency, current_load, health_score,
                    last_heartbeat_at, registered_at, instance_key, drain
                ) VALUES (
                    :id, :ws, 'lumora-worker-1', ARRAY['scripting'],
                    'busy'::worker_status, 2, 1, 98, :heartbeat, :registered,
                    :instance_key, false
                )
                """
            ),
            {
                "id": str(worker_id),
                "ws": workspace_id,
                "heartbeat": now,
                "registered": now,
                "instance_key": f"test-{worker_id}",
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO stage_assignments (
                    id, workspace_id, pipeline_run_id, stage, attempt_number,
                    worker_id, status, idempotency_key, lease_expires_at,
                    dispatched_at, priority, provider
                ) VALUES (
                    :id, :ws, :run, 'scripting'::content_stage, 2, :worker,
                    'acknowledged'::stage_assignment_status, :idem,
                    :lease, :dispatched, 0, 'draft_desk'
                )
                """
            ),
            {
                "id": str(assignment_id),
                "ws": workspace_id,
                "run": run_id,
                "worker": str(worker_id),
                "idem": f"ops-{assignment_id}",
                "lease": now + timedelta(minutes=5),
                "dispatched": now,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO job_schedule (
                    id, workspace_id, job_type, ref_table, ref_id, run_after,
                    status, attempt, priority
                ) VALUES (
                    :id, :ws, 'retry'::job_type, 'scripting', :run, :run_after,
                    'pending'::job_schedule_status, 1, 0
                )
                """
            ),
            {
                "id": str(job_id),
                "ws": workspace_id,
                "run": run_id,
                "run_after": now,
            },
        )
        await session.commit()

    monkeypatch.setenv("DEPLOYMENT_GIT_BRANCH", "main")
    monkeypatch.setenv("DEPLOYMENT_COMMIT_SHA", "abc123def456")
    monkeypatch.setenv("DEPLOYMENT_AT", "2026-08-06T05:00:00Z")
    monkeypatch.setenv("DEPLOYMENT_CI_STATUS", "success")
    monkeypatch.setenv("DEPLOYMENT_CI_URL", "https://ci.example/runs/1")
    get_settings.cache_clear()
    try:
        executive = await client.get(
            f"/workspaces/{workspace_id}/operations/executive", headers=headers
        )
        assert executive.status_code == 200, executive.text
        summary = executive.json()
        assert summary["workers_busy"] >= 1
        assert summary["jobs_running"] == 1
        # RETRY + the real review-timeout job created by Content Desk.
        assert summary["jobs_queued"] == 2
        assert summary["human_reviews_waiting"] == 1
        assert float(summary["spend_today_usd"]) > 0
        assert summary["deployment"]["git_branch"] == "main"
        assert summary["deployment"]["ci_status"] == "success"

        workers = await client.get(
            f"/workspaces/{workspace_id}/operations/workers", headers=headers
        )
        assert workers.status_code == 200
        worker = next(
            item
            for item in workers.json()["workers"]
            if item["name"] == "lumora-worker-1"
        )
        assert worker["name"] == "lumora-worker-1"
        assert worker["current_job"].startswith("scripting")
        assert worker["retry_count"] == 1
        assert worker["lease_status"] == "active"

        pipelines = await client.get(
            f"/workspaces/{workspace_id}/operations/pipelines", headers=headers
        )
        assert pipelines.status_code == 200
        pipeline_data = pipelines.json()
        assert pipeline_data["active_pipelines"] == 1
        assert pipeline_data["retrying_pipelines"] == 1
        assert pipeline_data["review_gates"] == 1
        assert pipeline_data["pipelines"][0]["id"] == run_id

        alerts = await client.get(
            f"/workspaces/{workspace_id}/operations/alerts", headers=headers
        )
        assert alerts.status_code == 200
        keys = {item["key"] for item in alerts.json()["alerts"]}
        assert "review_waiting" in keys
    finally:
        for key in (
            "DEPLOYMENT_GIT_BRANCH",
            "DEPLOYMENT_COMMIT_SHA",
            "DEPLOYMENT_AT",
            "DEPLOYMENT_CI_STATUS",
            "DEPLOYMENT_CI_URL",
        ):
            monkeypatch.delenv(key, raising=False)
        get_settings.cache_clear()


@pytest.mark.asyncio
async def test_operations_dashboard_requires_admin(client, new_user):
    _owner_id, _token, owner_headers = new_user
    workspace = await client.post(
        "/workspaces", headers=owner_headers, json={"name": "Private Operations"}
    )
    workspace_id = workspace.json()["id"]

    email = f"{uuid.uuid4()}@example.com"
    outsider = await client.post(
        "/auth/signup", json={"email": email, "password": "securepass1-beta"}
    )
    outsider_headers = {
        "Authorization": f"Bearer {outsider.json()['access_token']}"
    }
    for endpoint in ("executive", "workers", "pipelines", "alerts"):
        response = await client.get(
            f"/workspaces/{workspace_id}/operations/{endpoint}",
            headers=outsider_headers,
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_operations_dashboard_empty_state_is_real_zeroes(
    client, new_user, monkeypatch
):
    for variable in (
        "DEPLOYMENT_CI_STATUS",
        "DEPLOYMENT_CI_URL",
        "DEPLOYMENT_GIT_BRANCH",
        "DEPLOYMENT_COMMIT_SHA",
        "DEPLOYMENT_AT",
    ):
        monkeypatch.delenv(variable, raising=False)
    get_settings.cache_clear()
    _user_id, _token, headers = new_user
    workspace = await client.post(
        "/workspaces", headers=headers, json={"name": "Empty Operations"}
    )
    workspace_id = workspace.json()["id"]
    executive = await client.get(
        f"/workspaces/{workspace_id}/operations/executive", headers=headers
    )
    assert executive.status_code == 200
    body = executive.json()
    assert body["jobs_running"] == 0
    assert body["jobs_queued"] == 0
    assert body["spend_today_usd"] == "0"
    assert body["deployment"]["ci_status"] == "unavailable"
    get_settings.cache_clear()
