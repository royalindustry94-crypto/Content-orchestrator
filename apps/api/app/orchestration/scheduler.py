"""Scheduler: polls due job_schedule rows, applies back-pressure/fairness,
leases them, and dispatches (design doc §4; amendment 2: back-pressure).
"""

from __future__ import annotations

import logging
import socket
import uuid
from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import JobScheduleStatus, JobType
from app.models.scheduling import JobSchedule, WorkspaceConcurrencyLimit
from app.orchestration import dispatcher
from app.orchestration.retry import compute_backoff_seconds

logger = logging.getLogger(__name__)

DEFAULT_MAX_PER_WORKSPACE_PER_TICK = 5
LEASE_SECONDS = 30
NO_WORKER_MAX_RETRIES = 20  # bounds the 'no eligible worker yet' reschedule loop
NO_WORKER_RETRY_BASE_SECONDS = 5
NO_WORKER_RETRY_MAX_SECONDS = 120


def _scheduler_owner_id() -> str:
    return f"{socket.gethostname()}:{uuid.uuid4().hex[:8]}"


async def _fairness_limits(session: AsyncSession,
    workspace_ids: set[uuid.UUID]) -> dict[uuid.UUID, int]:
    if not workspace_ids:
        return {}
    result = await session.execute(
        select(WorkspaceConcurrencyLimit).where(
            WorkspaceConcurrencyLimit.workspace_id.in_(workspace_ids)
        )
    )
    limits = {row.workspace_id: row.max_per_scheduler_tick for row in result.scalars().all()}
    for ws in workspace_ids:
        limits.setdefault(ws, DEFAULT_MAX_PER_WORKSPACE_PER_TICK)
    return limits


async def poll_and_lease(session: AsyncSession, *, batch_size: int = 100) -> list[JobSchedule]:
    """One scheduler tick. Selects due work with FOR UPDATE SKIP LOCKED
    (so N schedulers partition safely — design doc §4.5), then applies
    weighted-round-robin fairness across workspaces (§4.6/4.7) so one
    tenant's backlog can't starve others within this tick. Aging (older
    run_after sorts first within a workspace) prevents indefinite
    starvation for any single job.
    """
    owner = _scheduler_owner_id()
    result = await session.execute(
        select(JobSchedule)
        .where(
            JobSchedule.status == JobScheduleStatus.PENDING,
            JobSchedule.run_after <= datetime.now(UTC),
        )
        .order_by(JobSchedule.priority.desc(), JobSchedule.run_after.asc())
        .limit(batch_size * 3)  # over-fetch; fairness trims below
        .with_for_update(skip_locked=True)
    )
    candidates = list(result.scalars().all())
    if not candidates:
        return []

    by_workspace: dict[uuid.UUID, list[JobSchedule]] = defaultdict(list)
    for job in candidates:
        by_workspace[job.workspace_id].append(job)

    limits = await _fairness_limits(session, set(by_workspace.keys()))
    leased: list[JobSchedule] = []
    # Round-robin across workspaces rather than draining one workspace's
    # whole allowance before moving to the next, so throughput is spread
    # even within a single tick.
    cursors = {ws: 0 for ws in by_workspace}
    while len(leased) < batch_size and any(
        cursors[ws] < min(len(jobs), limits[ws]) for ws, jobs in by_workspace.items()
    ):
        for ws, jobs in by_workspace.items():
            if len(leased) >= batch_size:
                break
            if cursors[ws] >= min(len(jobs), limits[ws]):
                continue
            job = jobs[cursors[ws]]
            cursors[ws] += 1
            job.status = JobScheduleStatus.LEASED
            job.lease_owner = owner
            job.lease_expires_at = datetime.now(UTC) + timedelta(seconds=LEASE_SECONDS)
            leased.append(job)

    return leased


async def reap_expired_leases(session: AsyncSession, *, batch_size: int = 100) -> int:
    result = await session.execute(
        select(JobSchedule)
        .where(
            JobSchedule.status == JobScheduleStatus.LEASED,
            JobSchedule.lease_expires_at < datetime.now(UTC),
        )
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    expired = list(result.scalars().all())
    for job in expired:
        job.status = JobScheduleStatus.PENDING
        job.lease_owner = None
        job.lease_expires_at = None
        job.attempt += 1
    return len(expired)


async def process_leased_job(session: AsyncSession, job: JobSchedule) -> None:
    """Execute the intention a job_schedule row represents. 'stage' and
    the two timeout types are implemented; 'recurring' has no concrete
    policy defined yet (no recurring job producers exist in this
    milestone) — it raises rather than silently no-opping, which is the
    honest behavior until a real recurring job type is introduced.
    """
    if job.job_type == JobType.STAGE or job.job_type == JobType.RETRY:
        assignment = await dispatcher.dispatch_stage(
            session,
            workspace_id=job.workspace_id,
            pipeline_run_id=job.ref_id,
            stage=job.ref_table,  # for stage/retry jobs, ref_table carries the stage_key
            attempt_number=job.attempt + 1,
            correlation_id=job.correlation_id or uuid.uuid4(),
            trace_id=job.trace_id,
        )
        if assignment is None or assignment.worker_id is None:
            # No eligible worker (or over the back-pressure cap) right
            # now — reschedule with backoff rather than dropping the
            # work (design doc §5.2). Bounded: after NO_WORKER_MAX_RETRIES
            # this stops looping forever and dead-letters instead, so a
            # stage with no registered worker doesn't retry indefinitely.
            job.attempt += 1
            if job.attempt >= NO_WORKER_MAX_RETRIES:
                from app.orchestration.retry import route_to_dead_letter

                job.status = JobScheduleStatus.CANCELLED
                await route_to_dead_letter(
                    session, workspace_id=job.workspace_id, related_table="job_schedule",
                    related_id=job.id, job_type=f"stage_dispatch:{job.ref_table}",
                    payload={"stage": job.ref_table, "pipeline_run_id": str(job.ref_id)},
                    failure_reason="no eligible worker available after repeated attempts",
                    attempt_count=job.attempt, first_failed_at=job.created_at,
                )
                return
            delay = compute_backoff_seconds(
                job.attempt, base_seconds=NO_WORKER_RETRY_BASE_SECONDS,
                multiplier=2, max_seconds=NO_WORKER_RETRY_MAX_SECONDS,
            )
            job.status = JobScheduleStatus.PENDING
            job.run_after = datetime.now(UTC) + timedelta(seconds=delay)
            job.lease_owner = None
            job.lease_expires_at = None
            return
        job.status = JobScheduleStatus.DONE
    elif job.job_type in (JobType.STAGE_TIMEOUT, JobType.REVIEW_TIMEOUT):
        from app.orchestration import controller  # local import: avoids a cycle at module load

        if job.job_type == JobType.STAGE_TIMEOUT:
            await controller.handle_stage_timeout(session, pipeline_run_id=job.ref_id,
                stage=job.ref_table)
        else:
            await controller.handle_review_timeout(session, review_gate_id=job.ref_id)
        job.status = JobScheduleStatus.DONE
    elif job.job_type == JobType.COMPENSATION:
        from app.orchestration import controller

        await controller.run_compensation_stage(session, pipeline_run_id=job.ref_id,
            stage=job.ref_table)
        job.status = JobScheduleStatus.DONE
    elif job.job_type == JobType.RECURRING:
        raise NotImplementedError(
            "recurring job_type has no policy defined in Milestone 4 — "
            "no recurring producer exists yet; add one before scheduling this type"
        )
    else:
        raise ValueError(f"unknown job_type: {job.job_type}")
