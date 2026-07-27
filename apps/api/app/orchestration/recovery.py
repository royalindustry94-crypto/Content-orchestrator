"""Lease recovery: requeue expired / orphaned assignments and route exhausted
recoveries to the dead-letter queue (Milestone 4 Workstream 3).

Every crash / stale-worker / lease-expiry scenario reduces to
``recover_assignment`` under ``FOR UPDATE`` on the assignment row. Batch
entry points use ``FOR UPDATE SKIP LOCKED`` so multi-replica ticks partition
work without double-requeue.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignments import StageAssignment
from app.models.enums import (
    RecoveryOutcome,
    RecoveryReason,
    StageAssignmentStatus,
    WorkerStatus,
)
from app.models.pipeline import PipelineRun
from app.models.recovery_audit import StageRecoveryAudit
from app.models.workers import WorkerRegistration
from app.models.workflow import WorkflowStage
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import STAGE_REASSIGNED
from app.orchestration.outbox import emit
from app.orchestration.retry import route_to_dead_letter


class RecoveryResultKind(str, Enum):
    REQUEUED = "requeued"
    DEAD_LETTERED = "dead_lettered"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class RecoveryResult:
    assignment: StageAssignment
    kind: RecoveryResultKind
    previous_attempt: int
    new_attempt: int | None


def _clear_lease_and_claim_fields(assignment: StageAssignment) -> None:
    assignment.worker_id = None
    assignment.lease_expires_at = None
    assignment.lease_started_at = None
    assignment.lease_extension_count = 0
    assignment.dispatched_at = None
    assignment.acknowledged_at = None
    assignment.claimed_by = None
    assignment.claimed_at = None
    assignment.claim_token = None


async def _release_worker_slot(
    session: AsyncSession, worker_id: uuid.UUID | None
) -> None:
    if worker_id is None:
        return
    worker = await session.get(WorkerRegistration, worker_id, with_for_update=True)
    if worker is None:
        return
    if worker.current_load > 0:
        worker.current_load -= 1
    if worker.status == WorkerStatus.BUSY and worker.current_load < worker.max_concurrency:
        worker.status = WorkerStatus.ONLINE


async def _resolve_max_attempts(
    session: AsyncSession, assignment: StageAssignment
) -> int:
    settings = get_settings()
    run = await session.get(PipelineRun, assignment.pipeline_run_id)
    if run is None or run.definition_id is None:
        return settings.assignment_default_max_attempts
    result = await session.execute(
        select(WorkflowStage).where(
            WorkflowStage.definition_id == run.definition_id,
            WorkflowStage.stage_key == assignment.stage,
        )
    )
    stage_def = result.scalar_one_or_none()
    if stage_def is None:
        return settings.assignment_default_max_attempts
    return stage_def.max_attempts

async def _audit(
    session: AsyncSession,
    *,
    assignment: StageAssignment,
    previous_worker_id: uuid.UUID | None,
    reason: RecoveryReason,
    previous_status: str,
    previous_attempt: int,
    new_attempt: int | None,
    outcome: RecoveryOutcome,
    detail: str | None,
) -> None:
    session.add(
        StageRecoveryAudit(
            id=uuid.uuid4(),
            workspace_id=assignment.workspace_id,
            assignment_id=assignment.id,
            previous_worker_id=previous_worker_id,
            reason=reason,
            previous_status=previous_status,
            previous_attempt=previous_attempt,
            new_attempt=new_attempt,
            outcome=outcome,
            detail=detail,
            correlation_id=assignment.correlation_id,
        )
    )


async def recover_assignment(
    session: AsyncSession,
    assignment: StageAssignment,
    *,
    reason: RecoveryReason,
    now: datetime | None = None,
    detail: str | None = None,
) -> RecoveryResult:
    """Recover one locked assignment. Caller must hold ``FOR UPDATE``.

    Returns SKIPPED if the row is no longer in an in-flight status (another
    transaction completed or recovered it first — should not happen under
    the lock, but defensive).
    """
    now = now or datetime.now(UTC)
    if assignment.status not in (
        StageAssignmentStatus.DISPATCHED,
        StageAssignmentStatus.ACKNOWLEDGED,
    ):
        await _audit(
            session,
            assignment=assignment,
            previous_worker_id=assignment.worker_id,
            reason=reason,
            previous_status=assignment.status.value,
            previous_attempt=assignment.attempt_number,
            new_attempt=None,
            outcome=RecoveryOutcome.SKIPPED,
            detail=detail or "not in-flight",
        )
        return RecoveryResult(
            assignment, RecoveryResultKind.SKIPPED, assignment.attempt_number, None
        )

    previous_worker_id = assignment.worker_id
    previous_attempt = assignment.attempt_number
    previous_status = assignment.status.value

    await _release_worker_slot(session, previous_worker_id)

    max_attempts = await _resolve_max_attempts(session, assignment)
    next_attempt = previous_attempt + 1

    if next_attempt > max_attempts:
        assignment.status = StageAssignmentStatus.FAILED
        assignment.completed_at = now
        _clear_lease_and_claim_fields(assignment)
        await route_to_dead_letter(
            session,
            workspace_id=assignment.workspace_id,
            related_table="stage_assignments",
            related_id=assignment.id,
            job_type=f"stage:{assignment.stage}",
            payload={
                "stage": assignment.stage.value
                if hasattr(assignment.stage, "value")
                else str(assignment.stage),
                "attempt_number": previous_attempt,
                "reason": reason.value,
            },
            failure_reason=f"recovery exhausted ({reason.value}) after {previous_attempt} attempts",
            attempt_count=previous_attempt,
            first_failed_at=assignment.dispatched_at or now,
        )
        run = await session.get(PipelineRun, assignment.pipeline_run_id)
        if run is not None and run.status not in ("failed", "succeeded", "cancelled"):
            from app.orchestration import controller

            if run.correlation_id is None:
                run.correlation_id = assignment.correlation_id or uuid.uuid4()
            await controller._fail_run(  # noqa: SLF001 — shared fail path
                session,
                run=run,
                reason=f"assignment recovery exhausted ({reason.value})",
            )
        await _audit(
            session,
            assignment=assignment,
            previous_worker_id=previous_worker_id,
            reason=reason,
            previous_status=previous_status,
            previous_attempt=previous_attempt,
            new_attempt=None,
            outcome=RecoveryOutcome.DEAD_LETTERED,
            detail=detail or f"max_attempts={max_attempts}",
        )
        return RecoveryResult(
            assignment, RecoveryResultKind.DEAD_LETTERED, previous_attempt, None
        )

    assignment.status = StageAssignmentStatus.PENDING
    assignment.attempt_number = next_attempt
    stage_val = (
        assignment.stage.value if hasattr(assignment.stage, "value") else str(assignment.stage)
    )
    assignment.idempotency_key = f"{assignment.pipeline_run_id}:{stage_val}:{next_attempt}"
    _clear_lease_and_claim_fields(assignment)

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
            "stage": stage_val,
            "assignment_id": str(assignment.id),
            "reason": reason.value,
            "previous_attempt": previous_attempt,
            "attempt_number": next_attempt,
        },
        produced_by="recovery",
    )
    await _audit(
        session,
        assignment=assignment,
        previous_worker_id=previous_worker_id,
        reason=reason,
        previous_status=previous_status,
        previous_attempt=previous_attempt,
        new_attempt=next_attempt,
        outcome=RecoveryOutcome.REQUEUED,
        detail=detail,
    )
    return RecoveryResult(
        assignment, RecoveryResultKind.REQUEUED, previous_attempt, next_attempt
    )


async def reap_expired_leases(
    session: AsyncSession,
    *,
    batch_size: int | None = None,
    now: datetime | None = None,
) -> list[RecoveryResult]:
    """Reap DISPATCHED/ACKNOWLEDGED rows whose lease has expired."""
    settings = get_settings()
    now = now or datetime.now(UTC)
    limit = batch_size if batch_size is not None else settings.assignment_reaper_batch_size
    result = await session.execute(
        select(StageAssignment)
        .where(
            StageAssignment.status.in_(
                [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
            ),
            StageAssignment.lease_expires_at.is_not(None),
            StageAssignment.lease_expires_at < now,
        )
        .order_by(StageAssignment.lease_expires_at.asc())
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    expired = list(result.scalars().all())
    outcomes: list[RecoveryResult] = []
    for assignment in expired:
        outcomes.append(
            await recover_assignment(
                session, assignment, reason=RecoveryReason.LEASE_EXPIRED, now=now
            )
        )
    return outcomes


async def reap_worker_assignments(
    session: AsyncSession,
    worker_id: uuid.UUID,
    *,
    reason: RecoveryReason,
    batch_size: int | None = None,
    now: datetime | None = None,
    detail: str | None = None,
) -> list[RecoveryResult]:
    """Reap every in-flight assignment still held by ``worker_id``.

    Loops in batches until none remain so a high-concurrency worker cannot
    leave orphan DISPATCHED rows after an offline/revoke/restart path.
    """
    settings = get_settings()
    now = now or datetime.now(UTC)
    limit = batch_size if batch_size is not None else settings.assignment_reaper_batch_size
    outcomes: list[RecoveryResult] = []
    while True:
        result = await session.execute(
            select(StageAssignment)
            .where(
                StageAssignment.worker_id == worker_id,
                StageAssignment.status.in_(
                    [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
                ),
            )
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        holdings = list(result.scalars().all())
        if not holdings:
            break
        for assignment in holdings:
            outcomes.append(
                await recover_assignment(
                    session, assignment, reason=reason, now=now, detail=detail
                )
            )
        if len(holdings) < limit:
            break
    return outcomes
