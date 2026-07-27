"""Atomic worker claiming (Milestone 4 Workstream 2 + WS4 priority/budgets).

A worker pulls at most one eligible stage assignment per claim. The whole
operation is one transaction on the service-role session (workers use
machine auth, not user JWT, so RLS user-scoping does not apply; workspace
scoping is enforced in the query predicate). Locking:

- the worker's own registry row is locked ``FOR UPDATE`` so its capacity
  math is serialized (two concurrent claims by the same worker cannot both
  read load=N);
- candidate assignments are locked ``FOR UPDATE SKIP LOCKED`` so N
  workers polling concurrently each grab *different* pending rows — the
  guarantee that two workers cannot claim one job.

WS4: candidates are ordered by effective priority (base + age boost)
descending, then ``created_at`` ascending. Rows whose provider concurrency
budget is exhausted are skipped so one saturated provider cannot block
another stage.

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

from app.core.config import get_settings
from app.models.assignments import StageAssignment
from app.models.claim_audit import StageClaimAudit
from app.models.enums import ClaimOutcome, StageAssignmentStatus, WorkerStatus
from app.models.workers import WorkerRegistration
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import STAGE_ASSIGNED
from app.orchestration.outbox import emit
from app.orchestration.priority import effective_priority_expr
from app.orchestration.provider_budgets import has_provider_capacity

# Back-compat module aliases; prefer Settings at call sites.
CLAIM_HEARTBEAT_MAX_AGE_SECONDS = 90
CLAIM_LEASE_SECONDS = 60


def _heartbeat_max_age() -> int:
    return get_settings().worker_offline_after_seconds


def _claim_lease_seconds() -> int:
    return get_settings().assignment_lease_seconds


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
            await _record(
                session,
                worker=worker,
                outcome=ClaimOutcome.GRANTED,
                reason="idempotent replay",
                assignment=existing,
                stage=existing.stage,
            )
            return ClaimResult(existing, ClaimOutcome.GRANTED, "idempotent replay")

    # 2. Worker eligibility (status / heartbeat freshness / capacity / drain).
    if worker.drain:
        reason = "worker is draining"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.INELIGIBLE,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.INELIGIBLE, reason)

    if worker.deregistered_at is not None or worker.status != WorkerStatus.ONLINE:
        reason = f"worker status is {worker.status.value}, not online"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.INELIGIBLE,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.INELIGIBLE, reason)

    if worker.last_heartbeat_at is None or (
        (now - worker.last_heartbeat_at).total_seconds() >= _heartbeat_max_age()
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

    # 3. Select eligible PENDING assignments ordered by effective priority
    #    (WS4), then created_at. SKIP LOCKED so concurrent claimers never
    #    contend for the same row. Over-budget providers are skipped.
    if not worker.supported_stages:
        reason = "worker supports no stages"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.NO_WORK,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.NO_WORK, reason)

    batch = get_settings().claim_candidate_batch_size
    effective = effective_priority_expr(
        StageAssignment.priority, StageAssignment.created_at, now=now
    )
    candidate = await session.execute(
        select(StageAssignment)
        .where(
            StageAssignment.workspace_id == worker.workspace_id,
            StageAssignment.status == StageAssignmentStatus.PENDING,
            StageAssignment.stage.in_(list(worker.supported_stages)),
        )
        .order_by(effective.desc(), StageAssignment.created_at.asc())
        .limit(batch)
        .with_for_update(skip_locked=True)
    )
    candidates = list(candidate.scalars().all())
    if not candidates:
        reason = "no eligible assignment"
        await _record(
            session, worker=worker, outcome=ClaimOutcome.NO_WORK,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, ClaimOutcome.NO_WORK, reason)

    assignment: StageAssignment | None = None
    saw_provider_budget_block = False
    for row in candidates:
        if not await has_provider_capacity(
            session, workspace_id=worker.workspace_id, provider=row.provider
        ):
            saw_provider_budget_block = True
            continue
        assignment = row
        break

    if assignment is None:
        reason = (
            "provider budget exhausted"
            if saw_provider_budget_block
            else "no eligible assignment"
        )
        outcome = ClaimOutcome.CAPACITY if saw_provider_budget_block else ClaimOutcome.NO_WORK
        await _record(
            session, worker=worker, outcome=outcome,
            reason=reason, assignment=None, stage=None,
        )
        return ClaimResult(None, outcome, reason)

    # 4. Mutate assignment + worker load in the SAME transaction.
    lease_seconds = _claim_lease_seconds()
    trace_id, span_id = child_span(assignment.trace_id)
    assignment.status = StageAssignmentStatus.DISPATCHED
    assignment.worker_id = worker.id
    assignment.claimed_by = worker.id
    assignment.claimed_at = now
    assignment.dispatched_at = now
    assignment.lease_expires_at = now + timedelta(seconds=lease_seconds)
    assignment.lease_started_at = now
    assignment.lease_extension_count = 0
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
            "priority": assignment.priority,
            "provider": assignment.provider,
        },
        produced_by="claiming",
    )
    await session.flush()
    return ClaimResult(assignment, ClaimOutcome.GRANTED, "claimed")
