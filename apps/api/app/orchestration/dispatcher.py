"""Dispatcher: worker selection, assignment lifecycle, lease management
(design doc §5).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignments import StageAssignment
from app.models.enums import StageAssignmentStatus, WorkerStatus
from app.models.pipeline import PipelineStageRun
from app.models.scheduling import WorkspaceConcurrencyLimit
from app.models.workers import WorkerRegistration
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import STAGE_ASSIGNED, STAGE_REASSIGNED
from app.orchestration.outbox import emit

# Default ack timeout: how long a dispatched-but-not-yet-acknowledged
# assignment waits before being treated as lost-ack (design doc §5.4).
ACK_TIMEOUT_SECONDS = 60
DEFAULT_MAX_CONCURRENT_ASSIGNMENTS = 10  # matches WorkspaceConcurrencyLimit's column default


async def select_worker(
    session: AsyncSession, *, stage_key: str, min_health_score: int = 50
) -> WorkerRegistration | None:
    """Rank: health desc, load asc, least-recently-heartbeated asc (a
    proxy for least-recently-used since assignment history isn't tracked
    per worker — documented simplification; a dedicated
    last_assigned_at column would refine this if load spreading proves
    uneven in practice).
    """
    result = await session.execute(
        select(WorkerRegistration)
        .where(
            WorkerRegistration.status.in_([WorkerStatus.ONLINE, WorkerStatus.BUSY]),
            WorkerRegistration.health_score >= min_health_score,
            WorkerRegistration.supported_stages.contains([stage_key]),
            WorkerRegistration.current_load < WorkerRegistration.max_concurrency,
        )
        .order_by(
            WorkerRegistration.health_score.desc(),
            WorkerRegistration.current_load.asc(),
            WorkerRegistration.last_heartbeat_at.asc().nulls_first(),
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    return result.scalar_one_or_none()


async def dispatch_stage(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    pipeline_run_id: uuid.UUID,
    stage: str,
    attempt_number: int,
    correlation_id: uuid.UUID,
    trace_id: str | None,
) -> StageAssignment | None:
    """Select a worker and create the assignment. Returns None (leaving
    the caller to reschedule) if no eligible worker exists right now —
    work is never dropped for lack of a worker (design doc §5.2).
    """
    # Back-pressure (amendment 2): a workspace may not exceed its configured
    # max_concurrent_assignments across dispatched/acknowledged assignments.
    # Checked before worker selection so an over-cap workspace never
    # consumes a worker slot at all — the assignment simply stays
    # unscheduled and is retried on a later tick (same as "no eligible
    # worker," §5.2), never dropped.
    limit_result = await session.execute(
        select(WorkspaceConcurrencyLimit).where(
            WorkspaceConcurrencyLimit.workspace_id == workspace_id
        )
    )
    limit_row = limit_result.scalar_one_or_none()
    max_concurrent = (
        limit_row.max_concurrent_assignments
        if limit_row
        else DEFAULT_MAX_CONCURRENT_ASSIGNMENTS
    )

    in_flight_result = await session.execute(
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.status.in_(
                [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
            ),
        )
    )
    if in_flight_result.scalar_one() >= max_concurrent:
        return None  # over back-pressure cap — caller reschedules, nothing is dropped

    worker = await select_worker(session, stage_key=stage)

    idempotency_key = f"{pipeline_run_id}:{stage}:{attempt_number}"
    existing = await session.execute(
        select(StageAssignment).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.idempotency_key == idempotency_key,
        )
    )
    already = existing.scalar_one_or_none()
    if already is not None:
        return already  # idempotent re-dispatch of the same attempt

    trace_id, span_id = child_span(trace_id)
    assignment = StageAssignment(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        pipeline_run_id=pipeline_run_id,
        stage=stage,
        attempt_number=attempt_number,
        worker_id=worker.id if worker else None,
        status=StageAssignmentStatus.DISPATCHED if worker else StageAssignmentStatus.PENDING,
        idempotency_key=idempotency_key,
        lease_expires_at=(
            datetime.now(UTC) + timedelta(seconds=ACK_TIMEOUT_SECONDS) if worker else None
        ),
        dispatched_at=datetime.now(UTC) if worker else None,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
    session.add(assignment)
    if worker is not None:
        worker.current_load += 1
        if worker.current_load >= worker.max_concurrency:
            worker.status = WorkerStatus.BUSY
    await session.flush()

    await emit(
        session,
        event_type=STAGE_ASSIGNED,
        workspace_id=workspace_id,
        aggregate_type="pipeline_run",
        aggregate_id=pipeline_run_id,
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_id=span_id,
        payload={
            "stage": stage, "attempt_number": attempt_number,
            "worker_id": str(worker.id) if worker else None,
            "assignment_id": str(assignment.id),
        },
        produced_by="dispatcher",
    )
    return assignment


async def acknowledge(session: AsyncSession, assignment: StageAssignment, *,
    lease_seconds: int) -> None:
    assignment.status = StageAssignmentStatus.ACKNOWLEDGED
    assignment.acknowledged_at = datetime.now(UTC)
    assignment.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)


async def renew_lease(session: AsyncSession, assignment: StageAssignment, *,
    lease_seconds: int) -> None:
    assignment.lease_expires_at = datetime.now(UTC) + timedelta(seconds=lease_seconds)


async def reap_expired_leases(session: AsyncSession, *,
    batch_size: int = 100) -> list[StageAssignment]:
    """Find assignments whose lease has expired while still dispatched/
    acknowledged, and return them to pending with a bumped attempt number
    — the mechanism every crash scenario reduces to (design doc §4.4, §11).
    """
    result = await session.execute(
        select(StageAssignment)
        .where(
            StageAssignment.status.in_(
                [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
            ),
            StageAssignment.lease_expires_at < datetime.now(UTC),
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    expired = list(result.scalars().all())
    for assignment in expired:
        if assignment.worker_id is not None:
            worker = await session.get(WorkerRegistration, assignment.worker_id)
            if worker is not None and worker.current_load > 0:
                worker.current_load -= 1
                if (
                    worker.status == WorkerStatus.BUSY
                    and worker.current_load < worker.max_concurrency
                ):
                    worker.status = WorkerStatus.ONLINE
        assignment.status = StageAssignmentStatus.PENDING
        assignment.worker_id = None
        assignment.lease_expires_at = None
        trace_id, span_id = child_span(assignment.trace_id)
        assignment.trace_id = trace_id
        await emit(
            session,
            event_type=STAGE_REASSIGNED,
            workspace_id=assignment.workspace_id,
            aggregate_type="pipeline_run",
            aggregate_id=assignment.pipeline_run_id,
            correlation_id=assignment.correlation_id or uuid.uuid4(),
            trace_id=trace_id,
            span_id=span_id,
            payload={
                "stage": assignment.stage,
                "assignment_id": str(assignment.id),
                "reason": "lease_expired",
            },
            produced_by="dispatcher.reaper",
        )
    return expired

async def submit_result(
    session,
    *,
    assignment: StageAssignment,
    success: bool,
    result: dict | None = None,
    error_message: str = "",
):
    """The real entry point for reporting a stage outcome (called by a
    worker's result-submission path — the reference client in this
    milestone, real generation workers later). This is a direct, in-
    process call into the controller within the SAME transaction as the
    assignment/stage-run bookkeeping — not a round-trip through the event
    bus, which would be a self-triggering loop (the controller's own
    handle_stage_success/failure are what EMIT stage.completed/
    stage.failed for other observers; they must not also be the
    consumers of their own output). See app.orchestration.consumers for
    the events that genuinely need bus-mediated decoupling (review
    decisions, made by a separate actor).
    """
    import uuid as _uuid
    from datetime import datetime

    from app.models.pipeline import PipelineRun
    from app.orchestration import controller

    assignment.status = StageAssignmentStatus.COMPLETED if success else StageAssignmentStatus.FAILED
    assignment.completed_at = datetime.now(UTC)
    assignment.result = result

    if assignment.worker_id is not None:
        worker = await session.get(WorkerRegistration, assignment.worker_id)
        if worker is not None and worker.current_load > 0:
            worker.current_load -= 1
            if worker.status == WorkerStatus.BUSY and worker.current_load < worker.max_concurrency:
                worker.status = WorkerStatus.ONLINE

    run = await session.get(PipelineRun, assignment.pipeline_run_id)
    if run is None:
        return

    stage_run = PipelineStageRun(
        id=_uuid.uuid4(), workspace_id=assignment.workspace_id,
        pipeline_run_id=assignment.pipeline_run_id, content_item_id=run.content_item_id,
        stage=assignment.stage, attempt_number=assignment.attempt_number,
        status="succeeded" if success else "failed",
        error_message=None if success else error_message,
        started_at=assignment.dispatched_at, completed_at=assignment.completed_at,
    )
    session.add(stage_run)
    await session.flush()

    from app.orchestration.events.envelope import child_span
    from app.orchestration.events.types import STAGE_COMPLETED
    from app.orchestration.outbox import emit as _emit

    if success:
        trace_id, span_id = child_span(assignment.trace_id)
        await _emit(
            session, event_type=STAGE_COMPLETED, workspace_id=assignment.workspace_id,
            aggregate_type="pipeline_run", aggregate_id=assignment.pipeline_run_id,
            correlation_id=assignment.correlation_id or run.correlation_id or _uuid.uuid4(),
            trace_id=trace_id, span_id=span_id,
            payload={
                "stage": assignment.stage, "attempt_number": assignment.attempt_number,
                "context": result or {},
            },
            produced_by="dispatcher",
        )
    if success:
        await controller.handle_stage_success(
            session, run=run, stage=assignment.stage, result_context=result or {}
        )
    else:
        await controller.handle_stage_failure(
            session, run=run, stage=assignment.stage,
            attempt_number=assignment.attempt_number, error_message=error_message,
        )

