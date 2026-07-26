"""Atomic worker claiming (Milestone 4 Workstream 2).

A worker pulls at most one eligible stage assignment per claim. The whole
operation is one transaction on the service-role session (workers use
machine auth, not user JWT, so RLS user-scoping does not apply; workspace
scoping is enforced in the query predicate). Locking:

- the worker's own registry row is locked ``FOR UPDATE`` so its capacity
  math is serialized (two concurrent claims by the same worker cannot both
  read load=N);
- the candidate assignment is locked ``FOR UPDATE SKIP LOCKED`` so N
  workers polling concurrently each grab a *different* pending row — the
  guarantee that two workers cannot claim one job.

Every attempt returns a ``ClaimResult`` and is recorded in
``stage_claim_audit``. Only ``GRANTED`` hands out work; capacity / stale /
offline / no-work are normal, audited non-grants — never silent failures.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignments import StageAssignment
from app.models.claim_audit import StageClaimAudit
from app.models.enums import ClaimOutcome, StageAssignmentStatus, WorkerStatus
from app.models.workers import WorkerRegistration
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import STAGE_ASSIGNED
from app.orchestration.outbox import emit

# How fresh a worker's last heartbeat must be to claim. Matches the WS1
# offline threshold: a worker the sweep would flip offline cannot claim.
CLAIM_HEARTBEAT_MAX_AGE_SECONDS = 90
# Lease granted on claim before the assignment is treated as lost (reaper
# returns it to pending). Mirrors the push dispatcher's ack timeout.
CLAIM_LEASE_SECONDS = 60


@dataclass(frozen=True)
class ClaimResult:
    assignment: StageAssignment | None
    outcome: ClaimOutcome
    reason: str


async def _record(
    session: AsyncSession,
    *,
    worker: WorkerRegistration,
    outcome: ClaimOutcome,
    reason: str,
    assignment: StageAssignment | None,
    stage: str | None,
) -> None:
    session.add(
        StageClaimAudit(
            id=uuid.uuid4(),
            workspace_id=worker.workspace_id,
            assignment_id=assignment.id if assignment is not None else None,
            worker_id=worker.id,
            outcome=outcome,
            stage=stage,
            detail=reason,
            correlation_id=assignment.correlation_id if assignment is not None else None,
        )
    )


async def claim_assignment(
    session: AsyncSession,
    *,
    worker_id: uuid.UUID,
    now: datetime | None = None,
    claim_token: uuid.UUID | None = None,
) -> ClaimResult:
    """Claim one eligible assignment for ``worker_id`` inside the caller's
    transaction. ``now`` is injectable for clock-controlled tests.

    ``claim_token`` makes a retried request idempotent: if the worker
    already holds an assignment (DISPATCHED, claimed by it) whose
    idempotency short-circuit matches, that same assignment is returned
    rather than consuming a second row.
    """
    now = now or datetime.now(UTC)

    # 1. Lock the worker row — serializes this worker's capacity accounting.
    worker = await session.get(WorkerRegistration, worker_id, with_for_update=True)
    if worker is None:
        # Credential authenticated but the registry row is gone: ineligible.
        return ClaimResult(None, ClaimOutcome.INELIGIBLE, "worker not found")

    # 1a. Idempotent replay: return the assignment already held under this token.
    if claim_token is not None:
        held = await session.execute(
            select(StageAssignment).where(
                StageAssignment.workspace_id == worker.workspace_id,
                StageAssignment.claimed_by == worker.id,
                StageAssignment.claim_token == claim_token,
                StageAssignment.status == StageAssignmentStatus.DISPATCHED,
            )
        )
        existing = held.scalar_one_or_none()
        if existing is not None:
            return ClaimResult(existing, ClaimOutcome.GRANTED, "idempotent replay")

    # 2. Worker eligibility (status / heartbeat freshness / capacity).
    if worker.deregistered_at is not None or worker.status != WorkerStatus.ONLINE:
        reason = f"worker status is {worker.status.value}, not online"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.INELIGIBLE,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.INELIGIBLE, reason)

    if worker.last_heartbeat_at is None or (
        (now - worker.last_heartbeat_at).total_seconds() >= CLAIM_HEARTBEAT_MAX_AGE_SECONDS
    ):
        reason = "heartbeat is stale"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.INELIGIBLE,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.INELIGIBLE, reason)

    if worker.current_load >= worker.max_concurrency:
        reason = "worker at maximum concurrency"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.CAPACITY,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.CAPACITY, reason)

    # 3. Select one eligible assignment: same workspace, a supported stage,
    #    still pending — oldest first (FIFO, bounds starvation). SKIP LOCKED
    #    so concurrent claimers never contend for the same row.
    if not worker.supported_stages:
        reason = "worker supports no stages"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.NO_WORK,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.NO_WORK, reason)

    candidate = await session.execute(
        select(StageAssignment)
        .where(
            StageAssignment.workspace_id == worker.workspace_id,
            StageAssignment.status == StageAssignmentStatus.PENDING,
            StageAssignment.stage.in_(list(worker.supported_stages)),
        )
        .order_by(StageAssignment.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    assignment = candidate.scalar_one_or_none()
    if assignment is None:
        reason = "no eligible assignment"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.NO_WORK,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.NO_WORK, reason)

    # 4. Mutate assignment + worker load in the SAME transaction.
    trace_id, span_id = child_span(assignment.trace_id)
    assignment.status = StageAssignmentStatus.DISPATCHED
    assignment.worker_id = worker.id
    assignment.claimed_by = worker.id
    assignment.claimed_at = now
    assignment.dispatched_at = now
    assignment.lease_expires_at = now + timedelta(seconds=CLAIM_LEASE_SECONDS)
    assignment.claim_count = (assignment.claim_count or 0) + 1
    assignment.claim_token = claim_token
    assignment.trace_id = trace_id

    worker.current_load += 1
    if worker.current_load >= worker.max_concurrency:
        worker.status = WorkerStatus.BUSY

    await _record(
        session, worker=worker, outcome=ClaimOutcome.GRANTED,
        reason="claimed", assignment=assignment, stage=assignment.stage,
    )
    await emit(
        session,
        event_type=STAGE_ASSIGNED,
        workspace_id=assignment.workspace_id,
        aggregate_type="pipeline_run",
        aggregate_id=assignment.pipeline_run_id,
        correlation_id=assignment.correlation_id or uuid.uuid4(),
        trace_id=trace_id,
        span_id=span_id,
        payload={
            "stage": assignment.stage,
            "attempt_number": assignment.attempt_number,
            "worker_id": str(worker.id),
            "assignment_id": str(assignment.id),
            "via": "claim",
        },
        produced_by="claiming",
    )
    await session.flush()
    return ClaimResult(assignment, ClaimOutcome.GRANTED, "claimed")
