"""Scheduler (leasing, fairness, expiry) and dispatcher (worker selection,
lease reaping) — design doc §4, §5, §11.
"""

import os
import uuid
from datetime import UTC, datetime, timedelta

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test")
os.environ.setdefault("APP_DATABASE_URL", "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.enums import JobScheduleStatus, JobType, StageAssignmentStatus, WorkerStatus
from app.models.scheduling import JobSchedule, WorkspaceConcurrencyLimit
from app.models.workers import WorkerRegistration
from app.orchestration import dispatcher, scheduler


async def _make_workspace(session):
    ws, user = str(uuid.uuid4()), str(uuid.uuid4())
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
        {"id": user, "e": f"{user}@x.com"},
    )
    await session.execute(
        text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"),
        {"id": ws, "u": user},
    )
    return uuid.UUID(ws)


@pytest.mark.asyncio
async def test_scheduler_fairness_caps_per_workspace_per_tick():
    async with AsyncSessionLocal() as session:
        # Isolate from shared-DB pollution: poll_and_lease over-fetches only
        # batch_size*3 candidates ordered by run_after ASC, so leftover due
        # PENDING jobs from earlier suite runs (which sort *before* this
        # test's now-dated jobs) can push our jobs out of the window. Retire
        # all pre-existing pending/leased jobs so only ours are due.
        await session.execute(
            text("UPDATE job_schedule SET status = 'cancelled' WHERE status IN "
                 "('pending'::job_schedule_status, 'leased'::job_schedule_status)")
        )
        ws_a = await _make_workspace(session)
        ws_b = await _make_workspace(session)
        session.add(WorkspaceConcurrencyLimit(
            id=uuid.uuid4(), workspace_id=ws_a, max_per_scheduler_tick=1,
        ))
        session.add(WorkspaceConcurrencyLimit(
            id=uuid.uuid4(), workspace_id=ws_b, max_per_scheduler_tick=1,
        ))
        # Workspace A floods 10 due jobs; B has 1. Fairness must not let A
        # consume the whole batch.
        for _ in range(10):
            session.add(JobSchedule(
                id=uuid.uuid4(), workspace_id=ws_a, job_type=JobType.STAGE_TIMEOUT,
                ref_table="x", ref_id=uuid.uuid4(), run_after=datetime.now(UTC),
            ))
        session.add(JobSchedule(
            id=uuid.uuid4(), workspace_id=ws_b, job_type=JobType.STAGE_TIMEOUT,
            ref_table="x", ref_id=uuid.uuid4(), run_after=datetime.now(UTC),
        ))
        await session.commit()

        leased = await scheduler.poll_and_lease(session, batch_size=100)
        await session.commit()

        from collections import Counter
        counts = Counter(job.workspace_id for job in leased)
        assert counts[ws_a] == 1, (
            "workspace A should be capped at its per-tick limit despite flooding"
        )
        assert counts[ws_b] == 1, "workspace B should still get its due job in the same tick"


@pytest.mark.asyncio
async def test_reap_expired_scheduler_leases_returns_to_pending():
    async with AsyncSessionLocal() as session:
        # Isolate: reap_expired_leases has a batch_size cap, so accumulated
        # expired leases from earlier runs could crowd out this test's job.
        await session.execute(
            text("UPDATE job_schedule SET status = 'cancelled' WHERE status IN "
                 "('pending'::job_schedule_status, 'leased'::job_schedule_status)")
        )
        ws = await _make_workspace(session)
        job = JobSchedule(
            id=uuid.uuid4(), workspace_id=ws, job_type=JobType.STAGE_TIMEOUT,
            ref_table="x", ref_id=uuid.uuid4(),
            run_after=datetime.now(UTC), status=JobScheduleStatus.LEASED,
            lease_owner="dead-scheduler",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=5),
        )
        session.add(job)
        await session.commit()

        n = await scheduler.reap_expired_leases(session)
        await session.commit()
        # n >= 1: the target job is always reaped; leftover leases from
        # earlier test-suite runs on this shared DB may also be reaped.
        assert n >= 1
        await session.refresh(job)
        assert job.status == JobScheduleStatus.PENDING
        assert job.attempt == 1


@pytest.mark.asyncio
async def test_dispatcher_selects_worker_by_health_and_load():
    async with AsyncSessionLocal() as session:
        # Workers are global (workspace_id=None). Park any pre-existing
        # ONLINE/BUSY workers so they don't compete with the test pair.
        await session.execute(
            text(
                "UPDATE worker_registry SET status = 'offline'::worker_status "
                "WHERE status IN ('online'::worker_status, 'busy'::worker_status)"
            )
        )

        weak = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name="weak", supported_stages=["scripting"],
            status=WorkerStatus.ONLINE, max_concurrency=5, current_load=0, health_score=40,
            last_heartbeat_at=datetime.now(UTC), registered_at=datetime.now(UTC),
        )
        strong = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name="strong", supported_stages=["scripting"],
            status=WorkerStatus.ONLINE, max_concurrency=5, current_load=0, health_score=90,
            last_heartbeat_at=datetime.now(UTC), registered_at=datetime.now(UTC),
        )
        session.add_all([weak, strong])
        await session.commit()

        chosen = await dispatcher.select_worker(session, stage_key="scripting")
        assert chosen is not None, "expected a worker to be selected"
        assert chosen.id == strong.id, (
            f"expected strong worker ({strong.id}) but got {chosen.id}; "
            "check that no other ONLINE workers with higher health_score were left in DB"
        )


@pytest.mark.asyncio
async def test_dispatcher_reaps_expired_assignment_lease_and_frees_worker_load():
    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name="w", supported_stages=["scripting"],
            status=WorkerStatus.BUSY, max_concurrency=1, current_load=1, health_score=100,
            last_heartbeat_at=datetime.now(UTC), registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": str(uuid.uuid4()), "ws": str(ws)},
        )
        from app.models.assignments import StageAssignment
        from app.models.pipeline import PipelineRun

        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": item_id, "ws": str(ws)},
        )
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=uuid.UUID(item_id))
        session.add(run)
        await session.flush()

        assignment = StageAssignment(
            id=uuid.uuid4(), workspace_id=ws, pipeline_run_id=run.id,
            stage="scripting", attempt_number=1,
            worker_id=worker.id, status=StageAssignmentStatus.DISPATCHED,
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=5),
        )
        session.add(assignment)
        await session.commit()

        expired = await dispatcher.reap_expired_leases(session)
        await session.commit()
        # >= 1: the target assignment is always reaped; leftover expired
        # assignments from earlier test-suite runs on the shared DB may also
        # be reaped. The important assertion is on the specific objects below.
        assert len(expired) >= 1
        await session.refresh(assignment)
        await session.refresh(worker)
        assert assignment.status == StageAssignmentStatus.PENDING
        assert assignment.worker_id is None
        assert worker.current_load == 0


@pytest.mark.asyncio
async def test_dispatcher_enforces_max_concurrent_assignments_back_pressure():
    """A workspace at its max_concurrent_assignments cap must not receive
    another dispatched assignment — dispatch_stage returns None and the
    stage stays unscheduled rather than exceeding the cap.
    """
    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        session.add(WorkspaceConcurrencyLimit(
            id=uuid.uuid4(), workspace_id=ws, max_concurrent_assignments=1,
        ))
        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": item_id, "ws": str(ws)},
        )
        from app.models.pipeline import PipelineRun

        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=uuid.UUID(item_id))
        session.add(run)
        await session.flush()

        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name="w", supported_stages=["scripting"],
            status=WorkerStatus.ONLINE, max_concurrency=5, current_load=0, health_score=100,
            last_heartbeat_at=datetime.now(UTC), registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.commit()

        first = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage="scripting",
            attempt_number=1, correlation_id=uuid.uuid4(), trace_id=None,
        )
        await session.commit()
        assert first is not None and first.worker_id is not None

        second = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage="scripting",
            attempt_number=2, correlation_id=uuid.uuid4(), trace_id=None,
        )
        assert second is None, (
            "workspace at its max_concurrent_assignments cap must not get a second dispatch"
        )
