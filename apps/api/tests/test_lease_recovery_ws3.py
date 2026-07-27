"""Workstream 3 acceptance tests: lease management, recovery & reliability.

Real PostgreSQL only. Clock-controlled where needed. Warnings are errors
via pytest -W error in CI. No mocks of the database.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, RuntimeSessionLocal
from app.models.assignments import StageAssignment
from app.models.enums import (
    RecoveryOutcome,
    RecoveryReason,
    StageAssignmentStatus,
    WorkerStatus,
)
from app.models.operations import DeadLetterJob
from app.models.provider_effects import ProviderEffectKey
from app.models.recovery_audit import StageRecoveryAudit
from app.models.workers import WorkerRegistration
from app.orchestration.provider_effects import ensure_provider_effect_key
from app.orchestration.recovery import reap_expired_leases, reap_worker_assignments
from app.services.workers import mark_stale_workers_offline

STAGE = "scripting"


async def _make_user() -> dict:
    from tests.conftest import make_token

    user_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
            {"id": user_id, "e": f"{user_id}@example.com"},
        )
        await session.commit()
    token = make_token(user_id=user_id)
    return {"user_id": user_id, "headers": {"Authorization": f"Bearer {token}"}}


async def _make_workspace(client, headers) -> str:
    r = await client.post("/workspaces", headers=headers, json={"name": "ws3"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def _provision(client, headers, workspace_id, *, stages=None, max_concurrency=2):
    r = await client.post(
        f"/workspaces/{workspace_id}/workers",
        headers=headers,
        json={
            "name": f"w-{uuid.uuid4().hex[:8]}",
            "supported_stages": stages or [STAGE],
            "max_concurrency": max_concurrency,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def _bring_online(client, provisioned, *, max_concurrency=2):
    wh = {"Authorization": f"Bearer {provisioned['worker_secret']}"}
    await client.post(
        "/workers/register",
        headers=wh,
        json={
            "supported_stages": [STAGE],
            "capabilities": {"protocol_version": 1, "providers": [], "features": []},
            "worker_version": "t",
            "max_concurrency": max_concurrency,
        },
    )
    await client.post(
        "/workers/heartbeat",
        headers=wh,
        json={"status": "online", "current_load": 0},
    )
    return wh


async def _seed_assignment(workspace_id, *, stage=STAGE, attempt=1) -> uuid.UUID:
    async with AsyncSessionLocal() as session:
        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id,:ws,'t')"),
            {"id": item_id, "ws": workspace_id},
        )
        from app.models.pipeline import PipelineRun

        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=uuid.UUID(workspace_id),
            content_item_id=uuid.UUID(item_id),
        )
        session.add(run)
        await session.flush()
        a = StageAssignment(
            id=uuid.uuid4(),
            workspace_id=uuid.UUID(workspace_id),
            pipeline_run_id=run.id,
            stage=stage,
            attempt_number=attempt,
            status=StageAssignmentStatus.PENDING,
            idempotency_key=f"{run.id}:{stage}:{attempt}",
            correlation_id=uuid.uuid4(),
        )
        session.add(a)
        await session.commit()
        return a.id


async def _claim(client, wh) -> dict:
    r = await client.post("/workers/claim", headers=wh, json={})
    assert r.status_code == 200, r.text
    assert r.json()["outcome"] == "granted"
    return r.json()["assignment"]


@pytest_asyncio.fixture
async def ctx(client):
    u = await _make_user()
    ws = await _make_workspace(client, u["headers"])
    # Retire leftovers scoped to THIS workspace only (shared-DB safety).
    async with AsyncSessionLocal() as s:
        await s.execute(
            text(
                "UPDATE stage_assignments SET status = 'cancelled' "
                "WHERE workspace_id = :ws "
                "AND status IN ('dispatched','acknowledged','pending')"
            ),
            {"ws": ws},
        )
        await s.commit()
    return {"client": client, "headers": u["headers"], "user_id": u["user_id"], "ws": ws}


# ---- ack / renew / submit ------------------------------------------------


@pytest.mark.asyncio
async def test_ack_transitions_and_extends_lease(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        before = a.lease_expires_at

    r = await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "acknowledged"
    assert body["lease_extension_count"] >= 1

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        assert a.status == StageAssignmentStatus.ACKNOWLEDGED
        assert a.acknowledged_at is not None
        assert a.lease_expires_at is not None and a.lease_expires_at >= before


@pytest.mark.asyncio
async def test_renew_extends_lease(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        before = a.lease_expires_at
        before_count = a.lease_extension_count

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 200, r.text
    assert r.json()["lease_extension_count"] == before_count + 1

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        assert a.lease_expires_at > before


@pytest.mark.asyncio
async def test_renew_rejects_non_owner(ctx):
    prov1 = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh1 = await _bring_online(ctx["client"], prov1)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh1)
    aid = assignment["id"]

    prov2 = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh2 = await _bring_online(ctx["client"], prov2)
    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh2)
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_renew_rejects_expired(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 409
    assert r.json()["detail"] == "lease_expired"


@pytest.mark.asyncio
async def test_renew_rejects_max_total_lease(ctx):
    settings = get_settings()
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        # Push lease_started_at so far back that any extension exceeds max.
        a.lease_started_at = datetime.now(UTC) - timedelta(
            seconds=settings.assignment_max_lease_seconds + 10
        )
        # Keep current lease alive so we hit max_lease_exceeded, not lease_expired.
        a.lease_expires_at = datetime.now(UTC) + timedelta(seconds=30)
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 409
    assert r.json()["detail"] == "max_lease_exceeded"


@pytest.mark.asyncio
async def test_renew_rejects_revoked_credential(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]

    r = await ctx["client"].post(
        f"/workspaces/{ctx['ws']}/workers/{prov['worker_id']}/credentials/revoke",
        headers=ctx["headers"],
    )
    assert r.status_code == 200

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_concurrent_renewals(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    async def _renew():
        return await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)

    results = await asyncio.gather(_renew(), _renew(), _renew())
    codes = sorted(r.status_code for r in results)
    assert codes.count(200) >= 1
    assert all(c in (200, 409) for c in codes)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        assert a.lease_extension_count >= 2  # ack + at least one renew


@pytest.mark.asyncio
async def test_duplicate_renew_after_reap(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code in (403, 409)


# ---- recovery ------------------------------------------------------------


@pytest.mark.asyncio
async def test_lease_expiry_requeues_with_attempt_bump(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    aid = await _seed_assignment(ctx["ws"])
    await _claim(ctx["client"], wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=2)
        await s.commit()

    async with AsyncSessionLocal() as s:
        outcomes = await reap_expired_leases(s)
        assert any(o.assignment.id == aid for o in outcomes)
        await s.commit()

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.PENDING
        assert a.attempt_number == 2
        assert a.idempotency_key.endswith(":2")
        assert a.lease_expires_at is None and a.lease_started_at is None
        audits = (
            (
                await s.execute(
                    select(StageRecoveryAudit).where(StageRecoveryAudit.assignment_id == aid)
                )
            )
            .scalars()
            .all()
        )
        assert len(audits) == 1
        assert audits[0].reason == RecoveryReason.LEASE_EXPIRED
        assert audits[0].outcome == RecoveryOutcome.REQUEUED
        assert audits[0].previous_attempt == 1
        assert audits[0].new_attempt == 2


@pytest.mark.asyncio
async def test_lease_recovery_under_contention(ctx):
    """Two concurrent reapers partition via SKIP LOCKED — no double bump."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=4)
    wh = await _bring_online(ctx["client"], prov, max_concurrency=4)
    claimed = []
    for _ in range(4):
        await _seed_assignment(ctx["ws"])
        claimed.append(await _claim(ctx["client"], wh))

    async with AsyncSessionLocal() as s:
        for c in claimed:
            a = await s.get(StageAssignment, uuid.UUID(c["id"]))
            a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    async def _reap():
        async with AsyncSessionLocal() as s:
            out = await reap_expired_leases(s, batch_size=100)
            await s.commit()
            return [o.assignment.id for o in out]

    left, right = await asyncio.gather(_reap(), _reap())
    combined = left + right
    assert len(combined) == len(set(combined))
    assert set(combined) >= {uuid.UUID(c["id"]) for c in claimed}


@pytest.mark.asyncio
async def test_renew_wins_race_against_reaper(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    # Lease still valid — reaper must miss; renew succeeds.
    async with AsyncSessionLocal() as s:
        outcomes = await reap_expired_leases(s)
        assert aid not in [o.assignment.id for o in outcomes]
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 200

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.ACKNOWLEDGED
        assert str(a.worker_id) == prov["worker_id"]


@pytest.mark.asyncio
async def test_reaper_wins_race_against_late_renew(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code in (403, 409)


@pytest.mark.asyncio
async def test_worker_crash_heartbeat_timeout_reaps(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])
    worker_id = uuid.UUID(prov["worker_id"])

    async with AsyncSessionLocal() as s:
        await s.execute(
            text(
                "UPDATE worker_registry SET last_heartbeat_at = now() - interval '120 seconds' "
                "WHERE id = :id"
            ),
            {"id": str(worker_id)},
        )
        flipped = await mark_stale_workers_offline(s, offline_after_seconds=90)
        assert worker_id in flipped
        outcomes = await reap_worker_assignments(s, worker_id, reason=RecoveryReason.WORKER_OFFLINE)
        assert any(o.assignment.id == aid for o in outcomes)
        await s.commit()

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.PENDING
        w = await s.get(WorkerRegistration, worker_id)
        assert w.status == WorkerStatus.OFFLINE
        assert w.current_load == 0


@pytest.mark.asyncio
async def test_stale_worker_cleanup(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    await _bring_online(ctx["client"], prov)
    worker_id = uuid.UUID(prov["worker_id"])

    async with AsyncSessionLocal() as s:
        await s.execute(
            text(
                "UPDATE worker_registry SET last_heartbeat_at = now() - interval '200 seconds', "
                "current_load = 1 WHERE id = :id"
            ),
            {"id": str(worker_id)},
        )
        flipped = await mark_stale_workers_offline(s, offline_after_seconds=90)
        await s.commit()
    assert worker_id in flipped

    async with AsyncSessionLocal() as s:
        w = await s.get(WorkerRegistration, worker_id)
        assert w.status == WorkerStatus.OFFLINE
        assert w.current_load == 0


@pytest.mark.asyncio
async def test_worker_restart_reaps_stale_holdings(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])

    # Simulate crash: holdings remain DISPATCHED while worker re-registers.
    r = await ctx["client"].post(
        "/workers/register",
        headers=wh,
        json={
            "supported_stages": [STAGE],
            "capabilities": {"protocol_version": 1, "providers": [], "features": []},
            "worker_version": "restarted",
            "max_concurrency": 2,
        },
    )
    assert r.status_code == 200, r.text

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.PENDING
        assert a.attempt_number == 2
        audits = (
            (
                await s.execute(
                    select(StageRecoveryAudit).where(
                        StageRecoveryAudit.assignment_id == aid,
                        StageRecoveryAudit.reason == RecoveryReason.WORKER_RESTART,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_shutdown_deregister_reaps(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])

    r = await ctx["client"].post("/workers/deregister", headers=wh)
    assert r.status_code == 200

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.PENDING
        audits = (
            (
                await s.execute(
                    select(StageRecoveryAudit).where(
                        StageRecoveryAudit.assignment_id == aid,
                        StageRecoveryAudit.reason == RecoveryReason.WORKER_DEREGISTERED,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(audits) == 1


@pytest.mark.asyncio
async def test_drain_blocks_claim(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])

    r = await ctx["client"].post(
        f"/workspaces/{ctx['ws']}/workers/{prov['worker_id']}/drain",
        headers=ctx["headers"],
        json={"drain": True},
    )
    assert r.status_code == 200

    # Heartbeat so status stays online but drain is set.
    await ctx["client"].post(
        "/workers/heartbeat", headers=wh, json={"status": "online", "current_load": 0}
    )
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.status_code == 200
    assert r.json()["outcome"] == "ineligible"
    assert "drain" in r.json()["reason"]


@pytest.mark.asyncio
async def test_recovery_exhaustion_routes_dlq(ctx):
    settings = get_settings()
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    # Seed at max attempts so next recovery exhausts.
    aid = await _seed_assignment(ctx["ws"], attempt=settings.assignment_default_max_attempts)
    await _claim(ctx["client"], wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    async with AsyncSessionLocal() as s:
        outcomes = await reap_expired_leases(s)
        match = [o for o in outcomes if o.assignment.id == aid]
        assert match and match[0].kind.value == "dead_lettered"
        await s.commit()

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        assert a.status == StageAssignmentStatus.FAILED
        dlq = (
            (
                await s.execute(
                    select(DeadLetterJob).where(
                        DeadLetterJob.related_table == "stage_assignments",
                        DeadLetterJob.related_id == aid,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(dlq) == 1


@pytest.mark.asyncio
async def test_provider_effect_key_prevents_duplicate(ctx):
    aid = await _seed_assignment(ctx["ws"])
    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        first = await ensure_provider_effect_key(
            s,
            workspace_id=a.workspace_id,
            assignment_id=a.id,
            attempt_number=a.attempt_number,
        )
        second = await ensure_provider_effect_key(
            s,
            workspace_id=a.workspace_id,
            assignment_id=a.id,
            attempt_number=a.attempt_number,
        )
        await s.commit()
    assert first.created is True
    assert second.created is False
    assert first.effect_key == second.effect_key


@pytest.mark.asyncio
async def test_submit_after_reap_rejected(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()
    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    r = await ctx["client"].post(
        f"/workers/assignments/{aid}/submit",
        headers=wh,
        json={"success": True, "result": {}},
    )
    assert r.status_code in (403, 409)


@pytest.mark.asyncio
async def test_submit_success_path(ctx):
    from app.models.pipeline import PipelineRun
    from app.models.workflow import WorkflowDefinition, WorkflowStage

    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)

    async with AsyncSessionLocal() as session:
        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id,:ws,'t')"),
            {"id": item_id, "ws": ctx["ws"]},
        )
        definition = WorkflowDefinition(
            id=uuid.uuid4(),
            workspace_id=uuid.UUID(ctx["ws"]),
            name="ws3-one",
            version=1,
        )
        session.add(definition)
        await session.flush()
        session.add(
            WorkflowStage(
                id=uuid.uuid4(),
                workspace_id=uuid.UUID(ctx["ws"]),
                definition_id=definition.id,
                stage_key=STAGE,
                ordinal=1,
                is_terminal=True,
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=uuid.UUID(ctx["ws"]),
            content_item_id=uuid.UUID(item_id),
            definition_id=definition.id,
            status="running",
            correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()
        a = StageAssignment(
            id=uuid.uuid4(),
            workspace_id=uuid.UUID(ctx["ws"]),
            pipeline_run_id=run.id,
            stage=STAGE,
            attempt_number=1,
            status=StageAssignmentStatus.PENDING,
            idempotency_key=f"{run.id}:{STAGE}:1",
            correlation_id=run.correlation_id,
        )
        session.add(a)
        await session.commit()
        aid = str(a.id)

    assignment = await _claim(ctx["client"], wh)
    assert assignment["id"] == aid
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    r = await ctx["client"].post(
        f"/workers/assignments/{aid}/submit",
        headers=wh,
        json={"success": True, "result": {"ok": True}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"
    # Key was reserved at ack; submit reports created=False (already reserved).
    assert r.json()["provider_effect_created"] is False

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        assert a.status == StageAssignmentStatus.COMPLETED
        keys = (
            (
                await s.execute(
                    select(ProviderEffectKey).where(ProviderEffectKey.assignment_id == a.id)
                )
            )
            .scalars()
            .all()
        )
        assert len(keys) == 1


@pytest.mark.asyncio
async def test_rollback_behaviour_failed_renew(ctx):
    """A failed renew (expired) must leave lease_extension_count unchanged."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        count_before = a.lease_extension_count
        expires_before = a.lease_expires_at
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 409

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        # Still DISPATCHED/ACK with expired lease — renew did not mutate.
        assert a.lease_extension_count == count_before
        assert a.status in (
            StageAssignmentStatus.DISPATCHED,
            StageAssignmentStatus.ACKNOWLEDGED,
        )
        assert a.lease_expires_at < expires_before


# ---- RLS adversarial -----------------------------------------------------


@pytest.mark.asyncio
async def test_recovery_audit_rls_adversarial(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()
    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    other = await _make_user()
    other_ws = await _make_workspace(ctx["client"], other["headers"])

    async with RuntimeSessionLocal() as s:
        await s.execute(
            text("SELECT set_config('request.jwt.claim.sub', :u, true)"),
            {"u": other["user_id"]},
        )
        rows = (
            (
                await s.execute(
                    select(StageRecoveryAudit).where(StageRecoveryAudit.assignment_id == aid)
                )
            )
            .scalars()
            .all()
        )
        assert rows == []

        with pytest.raises((ProgrammingError, DBAPIError)):
            s.add(
                StageRecoveryAudit(
                    id=uuid.uuid4(),
                    workspace_id=uuid.UUID(other_ws),
                    assignment_id=uuid.uuid4(),
                    reason=RecoveryReason.LEASE_EXPIRED,
                    previous_status="dispatched",
                    previous_attempt=1,
                    outcome=RecoveryOutcome.REQUEUED,
                )
            )
            await s.flush()


@pytest.mark.asyncio
async def test_provider_effect_keys_rls_adversarial(ctx):
    aid = await _seed_assignment(ctx["ws"])
    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        await ensure_provider_effect_key(
            s,
            workspace_id=a.workspace_id,
            assignment_id=a.id,
            attempt_number=1,
        )
        await s.commit()
        ws_id = a.workspace_id

    other = await _make_user()
    await _make_workspace(ctx["client"], other["headers"])

    async with RuntimeSessionLocal() as s:
        await s.execute(
            text("SELECT set_config('request.jwt.claim.sub', :u, true)"),
            {"u": other["user_id"]},
        )
        rows = (
            (
                await s.execute(
                    select(ProviderEffectKey).where(ProviderEffectKey.workspace_id == ws_id)
                )
            )
            .scalars()
            .all()
        )
        assert rows == []

        with pytest.raises((ProgrammingError, DBAPIError)):
            s.add(
                ProviderEffectKey(
                    id=uuid.uuid4(),
                    workspace_id=ws_id,
                    assignment_id=aid,
                    attempt_number=1,
                    effect_key=f"forge-{uuid.uuid4()}",
                    effect_kind="stage_execute",
                )
            )
            await s.flush()


@pytest.mark.asyncio
async def test_member_can_read_own_recovery_audit(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()
    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    async with RuntimeSessionLocal() as s:
        await s.execute(
            text("SELECT set_config('request.jwt.claim.sub', :u, true)"),
            {"u": ctx["user_id"]},
        )
        rows = (
            (
                await s.execute(
                    select(StageRecoveryAudit).where(StageRecoveryAudit.assignment_id == aid)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_migration_0027_columns_present():
    async with AsyncSessionLocal() as s:
        cols = (
            await s.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = 'stage_assignments' "
                    "AND column_name IN ('lease_started_at','lease_extension_count')"
                )
            )
        ).fetchall()
        assert {c[0] for c in cols} == {"lease_started_at", "lease_extension_count"}
        tables = (
            await s.execute(
                text(
                    "SELECT tablename FROM pg_tables WHERE schemaname='public' "
                    "AND tablename IN ('stage_recovery_audit','provider_effect_keys')"
                )
            )
        ).fetchall()
        assert {t[0] for t in tables} == {"stage_recovery_audit", "provider_effect_keys"}


@pytest.mark.asyncio
async def test_submit_rejects_expired_lease_before_reaper(ctx):
    """Submit must refuse an expired lease even if the reaper has not run."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()

    r = await ctx["client"].post(
        f"/workers/assignments/{aid}/submit",
        headers=wh,
        json={"success": True, "result": {}},
    )
    assert r.status_code == 409
    assert r.json()["detail"] == "lease_expired"

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, uuid.UUID(aid))
        assert a.status == StageAssignmentStatus.ACKNOWLEDGED


@pytest.mark.asyncio
async def test_ack_reserves_provider_effect_key(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])
    r = await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)
    assert r.status_code == 200

    async with AsyncSessionLocal() as s:
        keys = (
            (
                await s.execute(
                    select(ProviderEffectKey).where(ProviderEffectKey.assignment_id == aid)
                )
            )
            .scalars()
            .all()
        )
        assert len(keys) == 1
        assert keys[0].effect_key == f"{aid}:1"
        # Duplicate reserve is a no-op (created=False), not an error.
        again = await ensure_provider_effect_key(
            s,
            workspace_id=keys[0].workspace_id,
            assignment_id=aid,
            attempt_number=1,
        )
        await s.commit()
    assert again.created is False


@pytest.mark.asyncio
async def test_renew_rechecks_revoked_credential_in_handler(ctx):
    """Credential re-check inside renew txn must see a committed revoke."""
    from app.models.enums import WorkerCredentialStatus
    from app.models.workers import WorkerCredential

    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = assignment["id"]
    await ctx["client"].post(f"/workers/assignments/{aid}/ack", headers=wh)

    # Simulate revoke committed while a request is "about to" renew: direct DB
    # revoke (same end state as admin revoke) then renew must 401.
    async with AsyncSessionLocal() as s:
        creds = (
            (
                await s.execute(
                    select(WorkerCredential).where(
                        WorkerCredential.worker_id == uuid.UUID(prov["worker_id"]),
                        WorkerCredential.status == WorkerCredentialStatus.ACTIVE,
                    )
                )
            )
            .scalars()
            .all()
        )
        for c in creds:
            c.status = WorkerCredentialStatus.REVOKED
        await s.commit()

    r = await ctx["client"].post(f"/workers/assignments/{aid}/renew", headers=wh)
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_recovery_audit_rejects_delete(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    assignment = await _claim(ctx["client"], wh)
    aid = uuid.UUID(assignment["id"])
    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, aid)
        a.lease_expires_at = datetime.now(UTC) - timedelta(seconds=1)
        await s.commit()
    async with AsyncSessionLocal() as s:
        await reap_expired_leases(s)
        await s.commit()

    async with AsyncSessionLocal() as s:
        row = (
            await s.execute(
                select(StageRecoveryAudit).where(StageRecoveryAudit.assignment_id == aid)
            )
        ).scalar_one()
        with pytest.raises(Exception) as exc:
            await s.execute(
                text("DELETE FROM stage_recovery_audit WHERE id = :id"),
                {"id": str(row.id)},
            )
            await s.commit()
        assert "immutable" in str(exc.value).lower()
