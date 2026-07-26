"""Workstream 2 acceptance tests: job queue & atomic claiming.

Real PostgreSQL only. Concurrency tests exercise genuine parallel
transactions (separate asyncpg connections) to prove FOR UPDATE SKIP
LOCKED hands one job to exactly one worker. RLS probes connect as
`app_runtime` with `request.jwt.claim.sub` set, exactly like production.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, ProgrammingError

from app.db.session import AsyncSessionLocal, RuntimeSessionLocal
from app.models.assignments import StageAssignment
from app.models.claim_audit import StageClaimAudit
from app.models.enums import ClaimOutcome, StageAssignmentStatus, WorkerStatus
from app.models.workers import WorkerRegistration
from app.orchestration import claiming

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
    r = await client.post("/workspaces", headers=headers, json={"name": "ws2"})
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


async def _bring_online(
    client, provisioned, *, current_load=0, status="online", max_concurrency=2
):
    """Register + heartbeat so the worker is ONLINE with a fresh heartbeat."""
    wh = {"Authorization": f"Bearer {provisioned['worker_secret']}"}
    await client.post(
        "/workers/register",
        headers=wh,
        json={
            "supported_stages": [STAGE],
            "capabilities": {"protocol_version": 1, "providers": [], "features": [STAGE]},
            "worker_version": "t",
            "max_concurrency": max_concurrency,
        },
    )
    await client.post(
        "/workers/heartbeat",
        headers=wh,
        json={"status": status, "current_load": current_load},
    )
    return wh


async def _seed_assignment(workspace_id, *, stage=STAGE, created_at=None) -> uuid.UUID:
    """Create a PENDING stage_assignment (+ backing content_item/run)."""
    async with AsyncSessionLocal() as session:
        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id,:ws,'t')"),
            {"id": item_id, "ws": workspace_id},
        )
        from app.models.pipeline import PipelineRun

        run = PipelineRun(
            id=uuid.uuid4(), workspace_id=uuid.UUID(workspace_id),
            content_item_id=uuid.UUID(item_id),
        )
        session.add(run)
        await session.flush()
        a = StageAssignment(
            id=uuid.uuid4(), workspace_id=uuid.UUID(workspace_id),
            pipeline_run_id=run.id, stage=stage, attempt_number=1,
            status=StageAssignmentStatus.PENDING,
            idempotency_key=f"{run.id}:{stage}:1",
            correlation_id=uuid.uuid4(),
        )
        if created_at is not None:
            a.created_at = created_at
        session.add(a)
        await session.commit()
        return a.id


@pytest_asyncio.fixture
async def ctx(client):
    u = await _make_user()
    ws = await _make_workspace(client, u["headers"])
    return {"client": client, "headers": u["headers"], "user_id": u["user_id"], "ws": ws}


# ---- happy path ----------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_claim(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    assignment_id = await _seed_assignment(ctx["ws"])

    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["outcome"] == "granted"
    assert body["assignment"]["id"] == str(assignment_id)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, assignment_id)
        assert a.status == StageAssignmentStatus.DISPATCHED
        assert str(a.worker_id) == prov["worker_id"]
        assert str(a.claimed_by) == prov["worker_id"]
        assert a.claimed_at is not None and a.lease_expires_at is not None
        assert a.claim_count == 1
        w = await s.get(WorkerRegistration, uuid.UUID(prov["worker_id"]))
        assert w.current_load == 1


@pytest.mark.asyncio
async def test_no_eligible_assignment(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.status_code == 200
    assert r.json()["outcome"] == "no_work"
    assert r.json()["assignment"] is None


@pytest.mark.asyncio
async def test_capability_mismatch(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"], stage="voiceover")  # worker only supports scripting
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "no_work"


@pytest.mark.asyncio
async def test_workspace_mismatch(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    # A pending assignment in a DIFFERENT workspace must be invisible.
    other = await _make_user()
    other_ws = await _make_workspace(ctx["client"], other["headers"])
    await _seed_assignment(other_ws)
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "no_work"


@pytest.mark.asyncio
async def test_revoked_worker_cannot_claim(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    # revoke all credentials
    r = await ctx["client"].post(
        f"/workspaces/{ctx['ws']}/workers/{prov['worker_id']}/credentials/revoke",
        headers=ctx["headers"],
    )
    assert r.status_code == 200
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_expired_credential_cannot_claim(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    async with AsyncSessionLocal() as s:
        await s.execute(
            text("UPDATE worker_credentials SET expires_at = :t WHERE worker_id = :w"),
            {"t": datetime.now(UTC) - timedelta(seconds=1), "w": prov["worker_id"]},
        )
        await s.commit()
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_stale_heartbeat_ineligible(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    async with AsyncSessionLocal() as s:
        await s.execute(
            text("UPDATE worker_registry SET last_heartbeat_at = :t WHERE id = :w"),
            {"t": datetime.now(UTC) - timedelta(seconds=200), "w": prov["worker_id"]},
        )
        await s.commit()
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "ineligible"
    assert "stale" in r.json()["reason"]


@pytest.mark.asyncio
async def test_offline_worker_ineligible(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    async with AsyncSessionLocal() as s:
        await s.execute(
            text("UPDATE worker_registry SET status='offline'::worker_status WHERE id = :w"),
            {"w": prov["worker_id"]},
        )
        await s.commit()
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "ineligible"


@pytest.mark.asyncio
async def test_worker_at_capacity(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=1)
    wh = await _bring_online(ctx["client"], prov, current_load=1, max_concurrency=1)
    await _seed_assignment(ctx["ws"])
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "capacity"


# ---- concurrency ---------------------------------------------------------

@pytest.mark.asyncio
async def test_two_workers_cannot_claim_one_job(ctx):
    """N workers, 1 pending assignment → exactly one 'granted'."""
    provs = [await _provision(ctx["client"], ctx["headers"], ctx["ws"]) for _ in range(5)]
    whs = [await _bring_online(ctx["client"], p) for p in provs]
    assignment_id = await _seed_assignment(ctx["ws"])

    results = await asyncio.gather(
        *[ctx["client"].post("/workers/claim", headers=wh, json={}) for wh in whs]
    )
    outcomes = [r.json()["outcome"] for r in results]
    assert outcomes.count("granted") == 1, outcomes
    granted = [r for r in results if r.json()["outcome"] == "granted"][0]
    assert granted.json()["assignment"]["id"] == str(assignment_id)

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, assignment_id)
        assert a.claim_count == 1  # claimed exactly once


@pytest.mark.asyncio
async def test_worker_cannot_exceed_max_concurrency_under_load(ctx):
    """1 worker (max 2), many assignments, concurrent claims → load never > 2."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=2)
    wh = await _bring_online(ctx["client"], prov)
    for _ in range(6):
        await _seed_assignment(ctx["ws"])

    results = await asyncio.gather(
        *[ctx["client"].post("/workers/claim", headers=wh, json={}) for _ in range(6)]
    )
    granted = sum(1 for r in results if r.json()["outcome"] == "granted")
    assert granted == 2, [r.json()["outcome"] for r in results]
    async with AsyncSessionLocal() as s:
        w = await s.get(WorkerRegistration, uuid.UUID(prov["worker_id"]))
        assert w.current_load == 2
        assert w.status == WorkerStatus.BUSY


# ---- idempotency & rollback ---------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_claim_token_returns_same_assignment(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=5)
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    token = str(uuid.uuid4())
    r1 = await ctx["client"].post("/workers/claim", headers=wh, json={"claim_token": token})
    r2 = await ctx["client"].post("/workers/claim", headers=wh, json={"claim_token": token})
    assert r1.json()["outcome"] == "granted"
    assert r2.json()["outcome"] == "granted"
    assert r1.json()["assignment"]["id"] == r2.json()["assignment"]["id"]
    async with AsyncSessionLocal() as s:
        w = await s.get(WorkerRegistration, uuid.UUID(prov["worker_id"]))
        assert w.current_load == 1  # only one row actually consumed


@pytest.mark.asyncio
async def test_rollback_restores_assignment_and_load(ctx):
    """If the transaction fails after mutation, nothing moves."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    await _bring_online(ctx["client"], prov)
    assignment_id = await _seed_assignment(ctx["ws"])

    async with AsyncSessionLocal() as session:
        result = await claiming.claim_assignment(
            session, worker_id=uuid.UUID(prov["worker_id"])
        )
        assert result.outcome == ClaimOutcome.GRANTED
        await session.rollback()  # simulate failure before commit

    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, assignment_id)
        assert a.status == StageAssignmentStatus.PENDING
        assert a.worker_id is None and a.claimed_by is None
        w = await s.get(WorkerRegistration, uuid.UUID(prov["worker_id"]))
        assert w.current_load == 0


@pytest.mark.asyncio
async def test_invalid_transition_claim_of_nonpending_skipped(ctx):
    """A dispatched (non-pending) row is never re-claimed."""
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    assignment_id = await _seed_assignment(ctx["ws"])
    async with AsyncSessionLocal() as s:
        a = await s.get(StageAssignment, assignment_id)
        a.status = StageAssignmentStatus.DISPATCHED
        await s.commit()
    r = await ctx["client"].post("/workers/claim", headers=wh, json={})
    assert r.json()["outcome"] == "no_work"


# ---- audit & RLS ---------------------------------------------------------

# ---- direct-service branch coverage (deterministic, not via ASGI) --------
# The claim service is exercised end-to-end through the API above, but the
# async tracer under-measures code reached through the ASGI transport (a
# known artifact, see WS1). These call the service directly so each
# eligibility branch is both proven and measured.

@pytest.mark.asyncio
async def test_service_worker_not_found(ctx):
    async with AsyncSessionLocal() as s:
        res = await claiming.claim_assignment(s, worker_id=uuid.uuid4())
    assert res.outcome == ClaimOutcome.INELIGIBLE
    assert "not found" in res.reason


@pytest.mark.asyncio
async def test_service_offline_and_stale_and_capacity_and_nowork(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=1)
    await _bring_online(ctx["client"], prov, max_concurrency=1)
    wid = uuid.UUID(prov["worker_id"])

    async def _set(**cols):
        async with AsyncSessionLocal() as s:
            w = await s.get(WorkerRegistration, wid)
            for k, v in cols.items():
                setattr(w, k, v)
            await s.commit()

    # offline → ineligible
    await _set(status=WorkerStatus.OFFLINE)
    async with AsyncSessionLocal() as s:
        r = await claiming.claim_assignment(s, worker_id=wid)
        assert r.outcome == ClaimOutcome.INELIGIBLE
        await s.commit()

    # online but stale heartbeat → ineligible
    await _set(
        status=WorkerStatus.ONLINE,
        last_heartbeat_at=datetime.now(UTC) - timedelta(seconds=999),
    )
    async with AsyncSessionLocal() as s:
        r = await claiming.claim_assignment(s, worker_id=wid)
        assert r.outcome == ClaimOutcome.INELIGIBLE and "stale" in r.reason
        await s.commit()

    # fresh + at capacity → capacity
    await _set(last_heartbeat_at=datetime.now(UTC), current_load=1)
    async with AsyncSessionLocal() as s:
        assert (await claiming.claim_assignment(s, worker_id=wid)).outcome == ClaimOutcome.CAPACITY
        await s.commit()

    # fresh + free but no supported stages → no_work
    await _set(current_load=0, supported_stages=[])
    async with AsyncSessionLocal() as s:
        r = await claiming.claim_assignment(s, worker_id=wid)
        assert r.outcome == ClaimOutcome.NO_WORK and "no stages" in r.reason
        await s.commit()

    # fresh + free + capable but nothing pending → no_work
    await _set(supported_stages=[STAGE])
    async with AsyncSessionLocal() as s:
        assert (await claiming.claim_assignment(s, worker_id=wid)).outcome == ClaimOutcome.NO_WORK
        await s.commit()


@pytest.mark.asyncio
async def test_service_granted_then_idempotent_replay(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"], max_concurrency=3)
    await _bring_online(ctx["client"], prov, max_concurrency=3)
    wid = uuid.UUID(prov["worker_id"])
    await _seed_assignment(ctx["ws"])
    token = uuid.uuid4()
    async with AsyncSessionLocal() as s:
        r1 = await claiming.claim_assignment(s, worker_id=wid, claim_token=token)
        await s.commit()
    async with AsyncSessionLocal() as s:
        r2 = await claiming.claim_assignment(s, worker_id=wid, claim_token=token)
        await s.commit()
    assert r1.outcome == ClaimOutcome.GRANTED and r2.outcome == ClaimOutcome.GRANTED
    assert r1.assignment.id == r2.assignment.id
    async with AsyncSessionLocal() as s:
        w = await s.get(WorkerRegistration, wid)
        assert w.current_load == 1


@pytest.mark.asyncio
async def test_claim_writes_audit_row(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    await ctx["client"].post("/workers/claim", headers=wh, json={})
    async with AsyncSessionLocal() as s:
        rows = (
            await s.execute(
                select(StageClaimAudit).where(
                    StageClaimAudit.worker_id == uuid.UUID(prov["worker_id"]),
                    StageClaimAudit.outcome == ClaimOutcome.GRANTED,
                )
            )
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].stage == "scripting"


@pytest.mark.asyncio
async def test_claim_audit_rls_blocks_cross_workspace_and_writes(ctx):
    prov = await _provision(ctx["client"], ctx["headers"], ctx["ws"])
    wh = await _bring_online(ctx["client"], prov)
    await _seed_assignment(ctx["ws"])
    await ctx["client"].post("/workers/claim", headers=wh, json={})

    # Owner (admin) of another workspace sees zero rows of this workspace's ledger.
    other = await _make_user()
    other_ws = await _make_workspace(ctx["client"], other["headers"])
    async with RuntimeSessionLocal() as s:
        await s.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
            {"sub": other["user_id"]},
        )
        visible = (
            await s.execute(
                text("SELECT count(*) FROM stage_claim_audit WHERE workspace_id = :ws"),
                {"ws": ctx["ws"]},
            )
        ).scalar_one()
        assert visible == 0
        # app_runtime has no INSERT grant/policy → write must be denied.
        with pytest.raises((ProgrammingError, DBAPIError)):
            await s.execute(
                text(
                    "INSERT INTO stage_claim_audit (workspace_id, worker_id, outcome) "
                    "VALUES (:ws, :w, 'granted')"
                ),
                {"ws": other_ws, "w": prov["worker_id"]},
            )
