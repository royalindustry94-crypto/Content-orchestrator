#!/usr/bin/env python3
"""Seed a visual-preview workspace for the Lumora Operations Dashboard.

Idempotent for the fixed demo admin email. Uses local auth + owner DB session
to insert representative workers / assignments / spend / leads / logs.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import UTC, datetime, timedelta
from urllib import error, request

API = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.environ["OPS_PREVIEW_EMAIL"]
PASSWORD = os.environ["OPS_PREVIEW_PASSWORD"]
WORKSPACE_NAME = os.environ.get("OPS_PREVIEW_WORKSPACE", "The Business Manager HQ")


def _http(method: str, path: str, *, token: str | None = None, body: dict | None = None):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = request.Request(f"{API}{path}", data=data, headers=headers, method=method)
    try:
        with request.urlopen(req) as resp:
            raw = resp.read().decode()
            return resp.status, json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            payload = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            payload = {"detail": raw}
        return exc.code, payload


def ensure_admin() -> str:
    status, payload = _http(
        "POST", "/auth/login", body={"email": EMAIL, "password": PASSWORD}
    )
    if status == 200 and payload.get("access_token"):
        return payload["access_token"]
    status, payload = _http(
        "POST", "/auth/signup", body={"email": EMAIL, "password": PASSWORD}
    )
    if status not in (200, 201) or not payload.get("access_token"):
        raise SystemExit(f"auth failed: {status} {payload}")
    return payload["access_token"]


def ensure_workspace(token: str) -> str:
    status, workspaces = _http("GET", "/workspaces", token=token)
    if status != 200:
        raise SystemExit(f"list workspaces failed: {status} {workspaces}")
    for row in workspaces:
        if row.get("name") == WORKSPACE_NAME:
            return row["id"]
    if workspaces:
        return workspaces[0]["id"]
    status, created = _http(
        "POST", "/workspaces", token=token, body={"name": WORKSPACE_NAME}
    )
    if status not in (200, 201):
        raise SystemExit(f"create workspace failed: {status} {created}")
    return created["id"]


def seed_via_api(token: str, workspace_id: str) -> list[str]:
    run_ids: list[str] = []
    topics = [
        ("Q3 product launch reel", "Hook the founder story in 8 seconds."),
        ("Customer win: Agency Desk", "Show the review gate in action."),
        ("Ops health walkthrough", "Narrate live workers and spend caps."),
    ]
    for topic, script in topics:
        status, body = _http(
            "POST",
            f"/workspaces/{workspace_id}/content-jobs",
            token=token,
            body={"topic": topic, "script_body": script},
        )
        if status in (200, 201):
            run_ids.append(body["pipeline_run_id"])
        elif status == 409:
            continue
        else:
            print(f"warn content-job {status}: {body}", file=sys.stderr)

    leads = [
        {
            "name": "Ada Founder",
            "company": "Northstar Media",
            "email": "ada@northstar.example",
            "source": "inbound",
            "status": "new",
            "notes": "Wants private beta seats",
            "follow_up_date": "2026-08-12",
        },
        {
            "name": "Ben Ops",
            "company": "Signal Collective",
            "email": "ben@signal.example",
            "source": "outbound",
            "status": "contacted",
            "notes": "Asked about spend controls",
            "follow_up_date": "2026-08-09",
        },
        {
            "name": "Cara Agency",
            "company": "Harbor Creative",
            "email": "cara@harbor.example",
            "source": "referral",
            "status": "qualified",
            "notes": "Ready for Mission Control demo",
            "follow_up_date": "2026-08-15",
        },
    ]
    for lead in leads:
        status, body = _http(
            "POST",
            f"/workspaces/{workspace_id}/operations/leads",
            token=token,
            body=lead,
        )
        if status not in (200, 201) and status != 409:
            # Duplicate email may 400/409 depending on constraints — ignore soft fails
            print(f"warn lead {lead['email']}: {status} {body}", file=sys.stderr)

    return run_ids


def seed_sql(workspace_id: str, run_ids: list[str]) -> None:
    # Owner connection for append-only ledgers / registry rows.
    import asyncio

    from sqlalchemy import text

    # Ensure API package imports resolve when run from repo root.
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "apps", "api"))
    os.chdir(os.path.join(os.path.dirname(__file__), "..", "apps", "api"))

    from app.db.session import AsyncSessionLocal

    async def _run() -> None:
        now = datetime.now(UTC)
        ws = uuid.UUID(workspace_id)
        workers = [
            ("lumora-draft-1", "busy", 1, 96, '{"cpu_percent": 48, "memory_percent": 55}'),
            ("lumora-voice-1", "online", 0, 99, '{"cpu_percent": 12, "memory_percent": 33}'),
            ("lumora-render-1", "busy", 2, 88, '{"cpu_percent": 71, "memory_percent": 64}'),
            (
                "lumora-stale-1",
                "offline",
                0,
                40,
                '{"cpu_percent": 0, "memory_percent": 0}',
            ),
        ]
        worker_ids: list[uuid.UUID] = []
        async with AsyncSessionLocal() as session:
            existing = await session.execute(
                text(
                    "SELECT count(*) FROM worker_registry "
                    "WHERE workspace_id = :ws AND name LIKE 'lumora-%'"
                ),
                {"ws": str(ws)},
            )
            if int(existing.scalar_one()) >= 3:
                print("workers already seeded; skipping registry inserts")
            else:
                for name, status, load, health, caps in workers:
                    wid = uuid.uuid4()
                    worker_ids.append(wid)
                    heartbeat = (
                        now - timedelta(minutes=45)
                        if status == "offline"
                        else now - timedelta(seconds=8)
                    )
                    await session.execute(
                        text(
                            """
                            INSERT INTO worker_registry (
                                id, workspace_id, name, supported_stages, status,
                                max_concurrency, current_load, health_score,
                                last_heartbeat_at, registered_at, instance_key,
                                drain, capabilities
                            ) VALUES (
                                :id, :ws, :name, ARRAY['scripting','voiceover','rendering'],
                                CAST(:status AS worker_status), 2, :load, :health,
                                :heartbeat, :registered, :instance_key, false,
                                CAST(:capabilities AS jsonb)
                            )
                            """
                        ),
                        {
                            "id": str(wid),
                            "ws": str(ws),
                            "name": name,
                            "status": status,
                            "load": load,
                            "health": health,
                            "heartbeat": heartbeat,
                            "registered": now - timedelta(hours=6),
                            "instance_key": f"preview-{wid}",
                            "capabilities": caps,
                        },
                    )

            # Attach a live assignment to first pipeline if present.
            if run_ids and worker_ids:
                assignment_id = uuid.uuid4()
                await session.execute(
                    text(
                        """
                        INSERT INTO stage_assignments (
                            id, workspace_id, pipeline_run_id, stage, attempt_number,
                            worker_id, status, idempotency_key, lease_expires_at,
                            dispatched_at, priority, provider
                        ) VALUES (
                            :id, :ws, :run, 'scripting'::content_stage, 1, :worker,
                            'acknowledged'::stage_assignment_status, :idem,
                            :lease, :dispatched, 0, 'draft_desk'
                        )
                        ON CONFLICT DO NOTHING
                        """
                    ),
                    {
                        "id": str(assignment_id),
                        "ws": str(ws),
                        "run": run_ids[0],
                        "worker": str(worker_ids[0]),
                        "idem": f"preview-{assignment_id}",
                        "lease": now + timedelta(minutes=5),
                        "dispatched": now - timedelta(minutes=1),
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
                        "id": str(uuid.uuid4()),
                        "ws": str(ws),
                        "run": run_ids[0],
                        "run_after": now,
                    },
                )
                await session.execute(
                    text(
                        """
                        INSERT INTO dead_letter_jobs (
                            id, workspace_id, related_table, related_id, job_type,
                            failure_reason, payload, attempt_count,
                            first_failed_at, last_failed_at, status
                        ) VALUES (
                            :id, :ws, 'pipeline_runs', :run, 'stage_retry',
                            'Provider timeout during voice synthesis',
                            CAST(:payload AS jsonb), 3,
                            :failed, :failed, 'pending'::dead_letter_status
                        )
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "ws": str(ws),
                        "run": run_ids[min(1, len(run_ids) - 1)],
                        "payload": json.dumps({"preview": True, "stage": "voice"}),
                        "failed": now - timedelta(hours=1),
                    },
                )
                for i, msg in enumerate(
                    (
                        ("info", "Draft desk claimed scripting assignment"),
                        ("warning", "Voice provider latency above budget"),
                        ("error", "Render worker retry scheduled"),
                    )
                ):
                    severity, message = msg
                    await session.execute(
                        text(
                            """
                            INSERT INTO worker_logs (
                                id, workspace_id, worker_id, pipeline_run_id,
                                assignment_id, severity, message, context,
                                occurred_at, received_at
                            ) VALUES (
                                :id, :ws, :worker, :run, :assignment,
                                :severity, :message,
                                CAST(:context AS jsonb), :occurred, :received
                            )
                            """
                        ),
                        {
                            "id": str(uuid.uuid4()),
                            "ws": str(ws),
                            "worker": str(worker_ids[min(i, len(worker_ids) - 1)]),
                            "run": run_ids[0],
                            "assignment": str(assignment_id),
                            "severity": severity,
                            "message": message,
                            "context": json.dumps({"preview": True, "i": i}),
                            "occurred": now - timedelta(minutes=10 - i),
                            "received": now - timedelta(minutes=10 - i),
                        },
                    )

            # Spend signal for cost panels / alerts.
            spend_exists = await session.execute(
                text(
                    "SELECT count(*) FROM spend_logs WHERE workspace_id = :ws "
                    "AND provider = 'openai'"
                ),
                {"ws": str(ws)},
            )
            if int(spend_exists.scalar_one()) == 0:
                await session.execute(
                    text(
                        """
                        INSERT INTO spend_logs (
                            id, workspace_id, provider, cost_usd, occurred_at
                        ) VALUES
                          (:id1, :ws, 'openai', 2.4500, :now),
                          (:id2, :ws, 'elevenlabs', 0.8200, :now),
                          (:id3, :ws, 'openai', 1.1000, :earlier)
                        """
                    ),
                    {
                        "id1": str(uuid.uuid4()),
                        "id2": str(uuid.uuid4()),
                        "id3": str(uuid.uuid4()),
                        "ws": str(ws),
                        "now": now,
                        "earlier": now - timedelta(hours=5),
                    },
                )

            await session.execute(
                text(
                    """
                    INSERT INTO workspace_billing (
                        workspace_id, plan, status, stripe_customer_id
                    ) VALUES (
                        :ws, 'pro', 'trialing', :customer
                    )
                    ON CONFLICT (workspace_id) DO UPDATE
                    SET plan = EXCLUDED.plan,
                        status = EXCLUDED.status,
                        stripe_customer_id = EXCLUDED.stripe_customer_id
                    """
                ),
                {"ws": str(ws), "customer": f"cus_preview_{ws.hex[:8]}"},
            )
            await session.commit()

    asyncio.run(_run())


def main() -> None:
    token = ensure_admin()
    workspace_id = ensure_workspace(token)
    run_ids = seed_via_api(token, workspace_id)
    seed_sql(workspace_id, run_ids)

    # Verify projections
    for path in (
        "executive",
        "workers",
        "pipelines",
        "alerts",
        "leads",
        "spend",
    ):
        status, body = _http(
            "GET", f"/workspaces/{workspace_id}/operations/{path}", token=token
        )
        print(f"{path}: {status}")
        if path == "executive" and status == 200:
            print(
                json.dumps(
                    {
                        k: body.get(k)
                        for k in (
                            "workers_online",
                            "workers_busy",
                            "jobs_running",
                            "jobs_queued",
                            "human_reviews_waiting",
                            "spend_today_usd",
                        )
                    }
                )
            )
        if path == "alerts" and status == 200:
            print("alerts:", [a.get("key") for a in body.get("alerts", [])][:8])
        if path == "leads" and status == 200:
            print("leads_total:", body.get("total"))
        if path == "workers" and status == 200:
            print("workers:", [w.get("name") for w in body.get("workers", [])][:6])

    print(
        json.dumps(
            {
                "email": EMAIL,
                "password": PASSWORD,
                "workspace_id": workspace_id,
                "workspace_name": WORKSPACE_NAME,
                "login_url": "http://localhost:5173/",
                "preview_url": "http://localhost:5173/",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
