"""Dispatcher: worker selection, assignment lifecycle, lease management
(design doc §5). Lease recovery (reap / attempt bump / DLQ) lives in
``app.orchestration.recovery`` (WS3); this module retains acknowledge,
renew, dispatch, and submit, and re-exports the reaper for callers that
imported it from here historically.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignments import StageAssignment
from app.models.enums import StageAssignmentStatus, WorkerStatus
from app.models.pipeline import PipelineStageRun
from app.models.scheduling import WorkspaceConcurrencyLimit
from app.models.workers import WorkerRegistration
from app.models.workspace import Workspace
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import STAGE_ASSIGNED
from app.orchestration.outbox import emit
from app.orchestration.priority import base_priority_for_tier
from app.orchestration.provider_budgets import has_provider_capacity
from app.orchestration.recovery import (  # noqa: F401 — re-export for existing callers/tests
    reap_expired_leases,
    reap_worker_assignments,
)

# Back-compat aliases — prefer Settings.assignment_lease_seconds.
ACK_TIMEOUT_SECONDS = 60
DEFAULT_MAX_CONCURRENT_ASSIGNMENTS = 10  # matches WorkspaceConcurrencyLimit's column default


class LeaseError(Exception):
    """Base for lease lifecycle violations (mapped to HTTP by routes)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class LeaseNotOwned(LeaseError):
    def __init__(self, message: str = "assignment not owned by worker") -> None:
        super().__init__("not_owned", message)


class LeaseConflict(LeaseError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(code, message)


def _lease_seconds() -> int:
    return get_settings().assignment_lease_seconds


def _max_lease_seconds() -> int:
    return get_settings().assignment_max_lease_seconds


def assert_lease_extendable(
    assignment: StageAssignment,
    *,
    worker_id: uuid.UUID,
    now: datetime | None = None,
    lease_seconds: int | None = None,
) -> None:
    """Raise LeaseError if the assignment cannot be ack'd / renewed by worker."""
    now = now or datetime.now(UTC)
    seconds = lease_seconds if lease_seconds is not None else _lease_seconds()
    if assignment.worker_id != worker_id:
        raise LeaseNotOwned()
    if assignment.status not in (
        StageAssignmentStatus.DISPATCHED,
        StageAssignmentStatus.ACKNOWLEDGED,
    ):
        raise LeaseConflict(
            "invalid_status",
            f"assignment status is {assignment.status.value}, expected dispatched or acknowledged",
        )
    if assignment.lease_expires_at is None or assignment.lease_expires_at < now:
        raise LeaseConflict(
            "lease_expired",
            "lease has expired; assignment is eligible for recovery",
        )
    started = assignment.lease_started_at or assignment.dispatched_at or now
    if now + timedelta(seconds=seconds) > started + timedelta(seconds=_max_lease_seconds()):
        raise LeaseConflict(
            "max_lease_exceeded",
            "renewal would exceed the maximum total lease duration",
        )


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
            WorkerRegistration.drain.is_(False),
            WorkerRegistration.deregistered_at.is_(None),
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
    provider: str | None = None,
    priority: int | None = None,
) -> StageAssignment | None:
    """Select a worker and create the assignment. Returns None (leaving
    the caller to reschedule) if no eligible worker exists right now —
    work is never dropped for lack of a worker (design doc §5.2).

    WS4: ``priority`` defaults from the workspace tier; ``provider`` is
    stored for budget accounting. When a provider budget is exhausted the
    assignment is still created as PENDING (never dropped).
    """
    lease_seconds = _lease_seconds()
    limit_result = await session.execute(
        select(WorkspaceConcurrencyLimit).where(
            WorkspaceConcurrencyLimit.workspace_id == workspace_id
        )
    )
    limit_row = limit_result.scalar_one_or_none()
    max_concurrent = (
        limit_row.max_concurrent_assignments if limit_row else DEFAULT_MAX_CONCURRENT_ASSIGNMENTS
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
        return None  # over workspace concurrency cap — caller reschedules, nothing is dropped

    if priority is None:
        workspace = await session.get(Workspace, workspace_id)
        priority = base_priority_for_tier(workspace.priority_tier if workspace is not None else 0)

    provider_ok = await has_provider_capacity(session, workspace_id=workspace_id, provider=provider)
    worker = await select_worker(session, stage_key=stage) if provider_ok else None

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

    now = datetime.now(UTC)
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
        lease_expires_at=(now + timedelta(seconds=lease_seconds) if worker else None),
        lease_started_at=now if worker else None,
        lease_extension_count=0,
        dispatched_at=now if worker else None,
        correlation_id=correlation_id,
        trace_id=trace_id,
        priority=priority,
        provider=provider,
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
            "stage": stage,
            "attempt_number": attempt_number,
            "worker_id": str(worker.id) if worker else None,
            "assignment_id": str(assignment.id),
            "priority": priority,
            "provider": provider,
        },
        produced_by="dispatcher",
    )
    return assignment


async def acknowledge(
    session: AsyncSession,
    assignment: StageAssignment,
    *,
    lease_seconds: int | None = None,
    worker_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> None:
    """DISPATCHED → ACKNOWLEDGED and extend the lease. When ``worker_id``
    is provided, ownership and bound checks are enforced (HTTP path).
    The legacy in-process path (reference client / tests) may omit it.
    """
    now = now or datetime.now(UTC)
    seconds = lease_seconds if lease_seconds is not None else _lease_seconds()
    if worker_id is not None:
        assert_lease_extendable(assignment, worker_id=worker_id, now=now, lease_seconds=seconds)
        if assignment.status != StageAssignmentStatus.DISPATCHED:
            raise LeaseConflict(
                "invalid_status",
                f"ack requires dispatched, got {assignment.status.value}",
            )
    assignment.status = StageAssignmentStatus.ACKNOWLEDGED
    assignment.acknowledged_at = now
    assignment.lease_expires_at = now + timedelta(seconds=seconds)
    if assignment.lease_started_at is None:
        assignment.lease_started_at = assignment.dispatched_at or now
    assignment.lease_extension_count = (assignment.lease_extension_count or 0) + 1


async def renew_lease(
    session: AsyncSession,
    assignment: StageAssignment,
    *,
    lease_seconds: int | None = None,
    worker_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> None:
    now = now or datetime.now(UTC)
    seconds = lease_seconds if lease_seconds is not None else _lease_seconds()
    if worker_id is not None:
        assert_lease_extendable(assignment, worker_id=worker_id, now=now, lease_seconds=seconds)
    assignment.lease_expires_at = now + timedelta(seconds=seconds)
    if assignment.lease_started_at is None:
        assignment.lease_started_at = assignment.dispatched_at or now
    assignment.lease_extension_count = (assignment.lease_extension_count or 0) + 1


async def submit_result(
    session,
    *,
    assignment: StageAssignment,
    success: bool,
    result: dict | None = None,
    error_message: str = "",
    worker_id: uuid.UUID | None = None,
    now: datetime | None = None,
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

    from app.models.pipeline import PipelineRun
    from app.orchestration import controller

    now = now or datetime.now(UTC)
    if worker_id is not None and assignment.worker_id != worker_id:
        raise LeaseNotOwned()
    if assignment.status not in (
        StageAssignmentStatus.DISPATCHED,
        StageAssignmentStatus.ACKNOWLEDGED,
    ):
        raise LeaseConflict(
            "invalid_status",
            f"submit requires in-flight status, got {assignment.status.value}",
        )
    # Lease is the uniform recovery signal: an expired lease means the
    # reaper owns the row. Submit must not race past expiry the way renew
    # already refuses to.
    if worker_id is not None and (
        assignment.lease_expires_at is None or assignment.lease_expires_at < now
    ):
        raise LeaseConflict(
            "lease_expired",
            "lease has expired; assignment is eligible for recovery",
        )

    assignment.status = StageAssignmentStatus.COMPLETED if success else StageAssignmentStatus.FAILED
    assignment.completed_at = now
    assignment.result = result
    assignment.lease_expires_at = None
    assignment.lease_started_at = None

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
        id=_uuid.uuid4(),
        workspace_id=assignment.workspace_id,
        pipeline_run_id=assignment.pipeline_run_id,
        content_item_id=run.content_item_id,
        stage=assignment.stage,
        attempt_number=assignment.attempt_number,
        status="succeeded" if success else "failed",
        error_message=None if success else error_message,
        started_at=assignment.dispatched_at,
        completed_at=assignment.completed_at,
    )
    session.add(stage_run)
    await session.flush()

    from app.orchestration.events.envelope import child_span
    from app.orchestration.events.types import STAGE_COMPLETED
    from app.orchestration.outbox import emit as _emit

    if success:
        trace_id, span_id = child_span(assignment.trace_id)
        await _emit(
            session,
            event_type=STAGE_COMPLETED,
            workspace_id=assignment.workspace_id,
            aggregate_type="pipeline_run",
            aggregate_id=assignment.pipeline_run_id,
            correlation_id=assignment.correlation_id or run.correlation_id or _uuid.uuid4(),
            trace_id=trace_id,
            span_id=span_id,
            payload={
                "stage": assignment.stage,
                "attempt_number": assignment.attempt_number,
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
            session,
            run=run,
            stage=assignment.stage,
            attempt_number=assignment.attempt_number,
            error_message=error_message,
        )
