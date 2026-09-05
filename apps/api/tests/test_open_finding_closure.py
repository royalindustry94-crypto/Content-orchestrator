"""Adversarial reproductions for the remaining OPEN / PARTIAL audit findings.

Real PostgreSQL only. Each test states the historical failure mode it
exercises so a reviewer can confirm the assertion is not weaker than the
finding it closes.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from app.db.session import AsyncSessionLocal
from app.models.assignments import StageAssignment
from app.models.enums import (
    JobScheduleStatus,
    JobType,
    ReservationStatus,
    StageAssignmentStatus,
    WorkerStatus,
)
from app.models.operations import DeadLetterJob
from app.models.pipeline import PipelineRun
from app.models.scheduling import JobSchedule
from app.models.spend import SpendReservation
from app.models.workers import WorkerRegistration
from app.models.workflow import WorkflowDefinition, WorkflowStage
from app.orchestration import controller, dispatcher, scheduler

STAGE = "scripting"


async def _make_workspace(session) -> uuid.UUID:
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


async def _one_stage_definition(session, workspace_id: uuid.UUID) -> WorkflowDefinition:
    definition = WorkflowDefinition(
        id=uuid.uuid4(), workspace_id=workspace_id, name=f"closure-{uuid.uuid4().hex[:6]}",
        version=1,
    )
    session.add(definition)
    await session.flush()
    session.add(
        WorkflowStage(
            id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
            stage_key=STAGE, ordinal=1, is_terminal=True, max_attempts=1,
        )
    )
    await session.flush()
    return definition


async def _make_run(session, workspace_id: uuid.UUID) -> PipelineRun:
    item_id = str(uuid.uuid4())
    await session.execute(
        text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
        {"id": item_id, "ws": str(workspace_id)},
    )
    definition = await _one_stage_definition(session, workspace_id)
    run = PipelineRun(
        id=uuid.uuid4(), workspace_id=workspace_id, content_item_id=uuid.UUID(item_id),
        definition_id=definition.id, status="running", correlation_id=uuid.uuid4(),
    )
    session.add(run)
    await session.flush()
    return run


async def _park_all_workers(session) -> None:
    """NO_WORKER requires that no eligible worker exists for the stage."""
    await session.execute(
        text(
            "UPDATE worker_registry SET status = 'offline'::worker_status "
            "WHERE status IN ('online'::worker_status, 'busy'::worker_status)"
        )
    )


async def _pending_assignments(session, run_id: uuid.UUID) -> int:
    return (
        await session.execute(
            select(func.count(StageAssignment.id)).where(
                StageAssignment.pipeline_run_id == run_id,
                StageAssignment.stage == STAGE,
                StageAssignment.status.in_(
                    [
                        StageAssignmentStatus.PENDING,
                        StageAssignmentStatus.DISPATCHED,
                        StageAssignmentStatus.ACKNOWLEDGED,
                    ]
                ),
            )
        )
    ).scalar_one()


async def _open_reservations(session, run_id: uuid.UUID) -> list[SpendReservation]:
    return list(
        (
            await session.execute(
                select(SpendReservation).where(
                    SpendReservation.pipeline_run_id == run_id,
                    SpendReservation.status == ReservationStatus.RESERVED,
                )
            )
        )
        .scalars()
        .all()
    )


# --- H-2: NO_WORKER retry must not mint duplicate pending assignments -----


@pytest.mark.asyncio
async def test_h2_no_worker_retry_keeps_single_pending_assignment():
    """Historical failure: a stage dispatched with no eligible worker was
    rescheduled, and each retry created another PENDING assignment row for
    the same stage, so a later worker could claim the same work twice.
    """
    async with AsyncSessionLocal() as session:
        await _park_all_workers(session)
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        job = JobSchedule(
            id=uuid.uuid4(),
            workspace_id=ws,
            job_type=JobType.STAGE,
            ref_table=STAGE,
            ref_id=run.id,
            run_after=datetime.now(UTC),
            status=JobScheduleStatus.LEASED,
            lease_owner="test-scheduler",
            lease_expires_at=datetime.now(UTC) + timedelta(seconds=60),
        )
        session.add(job)
        await session.commit()

        # Tick 1: no worker exists -> PENDING assignment is created.
        await scheduler.process_leased_job(session, job)
        await session.commit()
        first_outcome_pending = await _pending_assignments(session, run.id)
        assert first_outcome_pending == 1

        # Tick 2 and 3: the scheduler retries the same stage. Historically
        # each retry minted a new PENDING row for a fresh attempt number.
        for _ in range(2):
            job.status = JobScheduleStatus.LEASED
            job.lease_owner = "test-scheduler"
            job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
            await scheduler.process_leased_job(session, job)
            await session.commit()

        assert await _pending_assignments(session, run.id) == 1, (
            "NO_WORKER retries must not create additional claimable assignments"
        )

        # A concurrent duplicate dispatch for the same attempt must be
        # absorbed by the idempotency key rather than creating a second row.
        result = await dispatcher.dispatch_stage(
            session,
            workspace_id=ws,
            pipeline_run_id=run.id,
            stage=STAGE,
            attempt_number=1,
            correlation_id=uuid.uuid4(),
            trace_id=None,
        )
        await session.commit()
        assert result.outcome == dispatcher.DispatchOutcome.IDEMPOTENT
        assert await _pending_assignments(session, run.id) == 1


@pytest.mark.asyncio
async def test_h2_concurrent_dispatch_same_attempt_is_serialized():
    """Two schedulers racing on the same (run, stage, attempt) must end with
    exactly one assignment row — the unique idempotency key is the guard.
    """
    async with AsyncSessionLocal() as session:
        await _park_all_workers(session)
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        await session.commit()
        run_id, workspace_id = run.id, ws

    async def _dispatch() -> str:
        async with AsyncSessionLocal() as s:
            try:
                result = await dispatcher.dispatch_stage(
                    s,
                    workspace_id=workspace_id,
                    pipeline_run_id=run_id,
                    stage=STAGE,
                    attempt_number=1,
                    correlation_id=uuid.uuid4(),
                    trace_id=None,
                )
                await s.commit()
                return result.outcome.value
            except Exception as exc:  # unique-violation loser is acceptable
                await s.rollback()
                return f"error:{type(exc).__name__}"

    outcomes = await asyncio.gather(_dispatch(), _dispatch())

    async with AsyncSessionLocal() as session:
        assert await _pending_assignments(session, run_id) == 1, (
            f"exactly one assignment must survive concurrent dispatch, outcomes={outcomes}"
        )
        rows = (
            await session.execute(
                select(func.count(StageAssignment.id)).where(
                    StageAssignment.pipeline_run_id == run_id,
                    StageAssignment.stage == STAGE,
                )
            )
        ).scalar_one()
        assert rows == 1, f"no duplicate attempt rows may persist, outcomes={outcomes}"


# --- H-3: DLQ terminal paths must not retain OPEN spend reservations ------


@pytest.mark.asyncio
async def test_h3_exhausted_retries_dlq_releases_spend_reservation():
    """Historical failure: a paid stage reserved spend, the worker failed,
    retries were exhausted, the job was dead-lettered, and the RESERVED row
    stayed open forever — permanently consuming the workspace budget.
    """
    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        reservation = await controller.reserve_spend(
            session,
            run=run,
            stage=STAGE,
            provider="openai",
            estimated_cost_usd=Decimal("0.50"),
        )
        await session.commit()
        assert reservation is not None
        assert len(await _open_reservations(session, run.id)) == 1

        # Permanent failure (not in the retryable marker set) -> DLQ + fail.
        await controller.handle_stage_failure(
            session,
            run=run,
            stage=STAGE,
            attempt_number=99,
            error_message="provider rejected request permanently",
        )
        await session.commit()

        dlq = (
            await session.execute(
                select(func.count(DeadLetterJob.id)).where(
                    DeadLetterJob.workspace_id == ws,
                    DeadLetterJob.related_id == run.id,
                )
            )
        ).scalar_one()
        assert dlq >= 1, "terminal failure must be dead-lettered"

        assert await _open_reservations(session, run.id) == [], (
            "no RESERVED spend row may survive a DLQ terminal transition"
        )
        await session.refresh(reservation)
        assert reservation.status == ReservationStatus.RELEASED


@pytest.mark.asyncio
async def test_h3_no_worker_never_holds_budget_without_an_owner():
    """Reproduced defect: dispatch_stage reserved spend even when no worker
    was selected. The scheduler then retired the job as DONE (H-2), so the
    bounded NO_WORKER dead-letter branch (the only path that released the
    reservation) was unreachable and the RESERVED row leaked forever.

    Invariant now enforced: while a stage has no owning worker, it holds no
    workspace budget; the reservation is taken when a worker claims it.
    """
    async with AsyncSessionLocal() as session:
        await _park_all_workers(session)
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        job = JobSchedule(
            id=uuid.uuid4(),
            workspace_id=ws,
            job_type=JobType.STAGE,
            ref_table=STAGE,
            ref_id=run.id,
            run_after=datetime.now(UTC),
            status=JobScheduleStatus.LEASED,
            lease_owner="test-scheduler",
            lease_expires_at=datetime.now(UTC) + timedelta(seconds=60),
            attempt=scheduler.NO_WORKER_MAX_RETRIES - 1,
        )
        session.add(job)
        await session.commit()

        # Tick with no eligible worker: a claimable PENDING row is created.
        await scheduler.process_leased_job(session, job)
        await session.commit()
        assert await _pending_assignments(session, run.id) == 1
        assert await _open_reservations(session, run.id) == [], (
            "an unassigned PENDING stage must not hold workspace budget"
        )

        # Repeated ticks while still worker-less must not accumulate budget.
        for _ in range(3):
            job.status = JobScheduleStatus.LEASED
            job.lease_owner = "test-scheduler"
            job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=60)
            await scheduler.process_leased_job(session, job)
            await session.commit()

        assert await _open_reservations(session, run.id) == [], (
            "NO_WORKER retries must never leak reservations"
        )
        assert await _pending_assignments(session, run.id) == 1

        # A worker then appears and claims the pending row: the reservation is
        # taken exactly once, at the moment ownership transfers.
        from app.orchestration.claiming import claim_assignment

        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=ws, name=f"w-{uuid.uuid4().hex[:6]}",
            supported_stages=[STAGE], status=WorkerStatus.ONLINE, max_concurrency=2,
            current_load=0, health_score=100, last_heartbeat_at=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.commit()

        claim = await claim_assignment(session, worker_id=worker.id)
        await session.commit()
        assert claim.assignment is not None, claim.reason
        assert len(await _open_reservations(session, run.id)) == 1, (
            "claiming a pending stage must reserve budget exactly once"
        )


@pytest.mark.asyncio
async def test_h3_dlq_recovery_does_not_double_reserve_or_double_commit():
    """Re-running a stage after a DLQ terminal state must not leave two open
    reservations, and committing the surviving reservation twice must be a
    no-op (single ledger entry).
    """
    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        first = await controller.reserve_spend(
            session, run=run, stage=STAGE, provider="openai",
            estimated_cost_usd=Decimal("0.25"),
        )
        await session.commit()
        assert first is not None

        # Recovery replays the stage: reserve again for the same (run, stage).
        second = await controller.reserve_spend(
            session, run=run, stage=STAGE, provider="openai",
            estimated_cost_usd=Decimal("0.25"),
        )
        await session.commit()
        assert second is not None and second.id != first.id
        open_rows = await _open_reservations(session, run.id)
        assert len(open_rows) == 1, "retry must not accumulate open reservations"
        assert open_rows[0].id == second.id
        await session.refresh(first)
        assert first.status == ReservationStatus.RELEASED

        await controller.commit_spend(
            session, run=run, reservation=second, actual_cost_usd=Decimal("0.25")
        )
        await session.commit()
        await controller.commit_spend(
            session, run=run, reservation=second, actual_cost_usd=Decimal("0.25")
        )
        await session.commit()

        ledger = (
            await session.execute(
                text(
                    "SELECT count(*) FROM spend_logs WHERE workspace_id = :ws "
                    "AND stage = :stage"
                ),
                {"ws": str(ws), "stage": STAGE},
            )
        ).scalar_one()
        assert ledger == 1, "duplicate commit must not double-charge the ledger"
        assert await _open_reservations(session, run.id) == []


@pytest.mark.asyncio
async def test_h3_worker_failure_submit_releases_reservation():
    """The worker result path (paid stage -> provider failure) must release
    the reservation as part of the same transaction as the failure handling.
    """
    async with AsyncSessionLocal() as session:
        await _park_all_workers(session)
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name=f"w-{uuid.uuid4().hex[:6]}",
            supported_stages=[STAGE], status=WorkerStatus.ONLINE, max_concurrency=2,
            current_load=0, health_score=100, last_heartbeat_at=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.commit()

        result = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage=STAGE,
            attempt_number=1, correlation_id=uuid.uuid4(), trace_id=None,
        )
        await session.commit()
        assert result.assignment is not None
        assert len(await _open_reservations(session, run.id)) == 1

        await dispatcher.submit_result(
            session,
            assignment=result.assignment,
            success=False,
            error_message="provider hard failure",
        )
        await session.commit()

        assert await _open_reservations(session, run.id) == [], (
            "a failed stage submission must not leave an open reservation"
        )


@pytest.mark.asyncio
async def test_successful_worker_submit_requires_open_spend_reservation():
    """A missing reservation must never become an untracked successful stage."""
    async with AsyncSessionLocal() as session:
        await _park_all_workers(session)
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)
        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name=f"w-{uuid.uuid4().hex[:6]}",
            supported_stages=[STAGE], status=WorkerStatus.ONLINE, max_concurrency=2,
            current_load=0, health_score=100, last_heartbeat_at=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.commit()

        dispatched = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage=STAGE,
            attempt_number=1, correlation_id=uuid.uuid4(), trace_id=None,
        )
        await session.commit()
        assert dispatched.assignment is not None
        reservations = await _open_reservations(session, run.id)
        assert len(reservations) == 1
        await session.delete(reservations[0])
        await session.commit()

        with pytest.raises(dispatcher.LeaseConflict) as exc_info:
            await dispatcher.submit_result(
                session,
                assignment=dispatched.assignment,
                success=True,
                result={"estimated_cost_usd": "0.00"},
            )
        assert exc_info.value.code == "spend_reservation_missing"
        assert dispatched.assignment.status == StageAssignmentStatus.DISPATCHED

        await session.refresh(run)
        assert run.status == "running"


# --- M-C: crashed attempts consume an attempt, bounded by max_attempts ----


@pytest.mark.asyncio
async def test_mc_crashed_attempt_consumes_attempt_and_cannot_exceed_max_attempts():
    """Ambiguity resolved (see recovery.ATTEMPT_CONSUMED_ON_RECOVERY): a
    crashed leased attempt consumes one execution attempt, and repeated
    crashes can never start the stage more than max_attempts times.
    """
    from app.orchestration import recovery

    assert recovery.ATTEMPT_CONSUMED_ON_RECOVERY is True

    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        run = await _make_run(session, ws)  # stage max_attempts = 1
        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name=f"w-{uuid.uuid4().hex[:6]}",
            supported_stages=[STAGE], status=WorkerStatus.ONLINE, max_concurrency=2,
            current_load=1, health_score=100, last_heartbeat_at=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.flush()
        assignment = StageAssignment(
            id=uuid.uuid4(), workspace_id=ws, pipeline_run_id=run.id, stage=STAGE,
            attempt_number=1, worker_id=worker.id,
            status=StageAssignmentStatus.ACKNOWLEDGED,
            idempotency_key=f"{run.id}:{STAGE}:1",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=30),
            lease_started_at=datetime.now(UTC) - timedelta(seconds=120),
            dispatched_at=datetime.now(UTC) - timedelta(seconds=120),
            correlation_id=run.correlation_id,
        )
        session.add(assignment)
        await session.commit()

        results = await recovery.reap_expired_leases(session)
        await session.commit()
        mine = [r for r in results if r.assignment.id == assignment.id]
        assert len(mine) == 1
        # max_attempts=1 and the crash consumed attempt 1 -> exhausted.
        assert mine[0].kind == recovery.RecoveryResultKind.DEAD_LETTERED
        await session.refresh(assignment)
        assert assignment.status == StageAssignmentStatus.FAILED
        assert assignment.attempt_number == 1, (
            "a consumed attempt is never silently rewound"
        )


@pytest.mark.asyncio
async def test_mc_requeued_attempt_bumps_monotonically_and_releases_budget():
    """A crash with attempts remaining requeues at attempt+1 and must not
    leave the workspace paying for an assignment nobody owns.
    """
    from app.orchestration import recovery

    async with AsyncSessionLocal() as session:
        ws = await _make_workspace(session)
        item_id = str(uuid.uuid4())
        await session.execute(
            text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
            {"id": item_id, "ws": str(ws)},
        )
        definition = WorkflowDefinition(
            id=uuid.uuid4(), workspace_id=ws, name=f"retry-{uuid.uuid4().hex[:6]}",
            version=1,
        )
        session.add(definition)
        await session.flush()
        session.add(
            WorkflowStage(
                id=uuid.uuid4(), workspace_id=ws, definition_id=definition.id,
                stage_key=STAGE, ordinal=1, is_terminal=True, max_attempts=3,
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(), workspace_id=ws, content_item_id=uuid.UUID(item_id),
            definition_id=definition.id, status="running", correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()

        worker = WorkerRegistration(
            id=uuid.uuid4(), workspace_id=None, name=f"w-{uuid.uuid4().hex[:6]}",
            supported_stages=[STAGE], status=WorkerStatus.ONLINE, max_concurrency=2,
            current_load=1, health_score=100, last_heartbeat_at=datetime.now(UTC),
            registered_at=datetime.now(UTC),
        )
        session.add(worker)
        await session.flush()
        assignment = StageAssignment(
            id=uuid.uuid4(), workspace_id=ws, pipeline_run_id=run.id, stage=STAGE,
            attempt_number=1, worker_id=worker.id,
            status=StageAssignmentStatus.ACKNOWLEDGED,
            idempotency_key=f"{run.id}:{STAGE}:1",
            lease_expires_at=datetime.now(UTC) - timedelta(seconds=30),
            lease_started_at=datetime.now(UTC) - timedelta(seconds=120),
            dispatched_at=datetime.now(UTC) - timedelta(seconds=120),
            correlation_id=run.correlation_id,
        )
        session.add(assignment)
        reservation = await controller.reserve_spend(
            session, run=run, stage=STAGE, provider="openai",
            estimated_cost_usd=Decimal("0.40"),
        )
        await session.commit()
        assert reservation is not None

        results = await recovery.reap_expired_leases(session)
        await session.commit()
        mine = [r for r in results if r.assignment.id == assignment.id]
        assert len(mine) == 1
        assert mine[0].kind == recovery.RecoveryResultKind.REQUEUED
        await session.refresh(assignment)
        assert assignment.attempt_number == 2
        assert assignment.status == StageAssignmentStatus.PENDING
        assert assignment.idempotency_key == f"{run.id}:{STAGE}:2"
        assert await _open_reservations(session, run.id) == [], (
            "a requeued, unowned assignment must not hold workspace budget"
        )
