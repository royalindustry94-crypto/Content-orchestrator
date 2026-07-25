"""Operational metrics (amendment 3).

No metrics backend (Prometheus/StatsD/etc.) is in the declared stack, so
this module takes the approach the design doc's §10.5 already committed
to: metrics are derivable from the durable tables, computed on demand by
these query functions, plus a lightweight structured-log counter/
histogram emitter for the instrumentation points that aren't naturally a
table query (e.g. "an assignment was just dispatched"). Wiring either
side to a real metrics backend later is a matter of calling these
functions on a schedule / forwarding the log lines — not a redesign.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignments import StageAssignment
from app.models.enums import JobScheduleStatus, OutboxEventStatus, StageAssignmentStatus
from app.models.events import OutboxEvent
from app.models.operations import DeadLetterJob
from app.models.pipeline import PipelineRun, PipelineStageRun
from app.models.scheduling import JobSchedule

logger = logging.getLogger("orchestration.metrics")


def emit_counter(name: str, value: int = 1, **labels: object) -> None:
    """Structured-log a counter increment. A real backend adapter would
    subscribe to these log lines (or this function would be swapped for
    a client library call) without touching call sites.
    """
    logger.info("metric.counter", extra={"metric": name, "value": value, **labels})


def emit_histogram(name: str, value: float, **labels: object) -> None:
    logger.info("metric.histogram", extra={"metric": name, "value": value, **labels})


# --- table-derived collectors ---------------------------------------------

async def queue_depth(session: AsyncSession) -> dict[str, int]:
    result = await session.execute(
        select(JobSchedule.status, func.count(JobSchedule.id)).group_by(JobSchedule.status)
    )
    return {status.value: count for status, count in result.all()}


async def event_latency_seconds(session: AsyncSession, *, sample_size: int = 500) -> dict[str,
    float]:
    """Average seconds between occurred_at and updated_at for recently
    dispatched events — a proxy for outbox relay latency.
    """
    result = await session.execute(
        select(func.avg(func.extract("epoch", OutboxEvent.updated_at - OutboxEvent.occurred_at)))
        .where(OutboxEvent.status == OutboxEventStatus.DISPATCHED)
        .order_by(OutboxEvent.occurred_at.desc())
        .limit(sample_size)
    )
    avg_seconds = result.scalar_one_or_none()
    return {"avg_dispatch_latency_seconds": float(avg_seconds) if avg_seconds is not None else 0.0}


async def workflow_execution_duration_seconds(
    session: AsyncSession, *, since: datetime | None = None
) -> dict[str, float]:
    since = since or (datetime.now(UTC) - timedelta(days=1))
    result = await session.execute(
        select(func.avg(func.extract("epoch", PipelineRun.completed_at - PipelineRun.started_at)))
        .where(
            PipelineRun.completed_at.isnot(None), PipelineRun.started_at.isnot(None),
            PipelineRun.completed_at >= since,
        )
    )
    avg_seconds = result.scalar_one_or_none()
    return {
        "avg_execution_duration_seconds": float(avg_seconds) if avg_seconds is not None else 0.0
    }


async def retry_counts(session: AsyncSession, *, since: datetime | None = None) -> int:
    since = since or (datetime.now(UTC) - timedelta(days=1))
    result = await session.execute(
        select(func.count(PipelineStageRun.id)).where(
            PipelineStageRun.status == "failed", PipelineStageRun.created_at >= since
        )
    )
    return result.scalar_one()


async def dead_letter_count(session: AsyncSession) -> int:
    result = await session.execute(
        select(func.count(DeadLetterJob.id)).where(DeadLetterJob.status == "pending")
    )
    return result.scalar_one()


async def dispatch_success_failure_rate(
    session: AsyncSession, *, since: datetime | None = None
) -> dict[str, float]:
    since = since or (datetime.now(UTC) - timedelta(days=1))
    result = await session.execute(
        select(StageAssignment.status, func.count(StageAssignment.id))
        .where(StageAssignment.created_at >= since)
        .group_by(StageAssignment.status)
    )
    counts = {status.value: count for status, count in result.all()}
    total = sum(counts.values()) or 1
    return {
        "success_rate": counts.get("completed", 0) / total,
        "failure_rate": counts.get("failed", 0) / total,
        **{f"count_{k}": v for k, v in counts.items()},
    }


async def worker_lease_contention(session: AsyncSession) -> int:
    """Assignments currently reclaimable (lease expired but not yet
    reaped) — a proxy for contention/backlog on the reaper.
    """
    result = await session.execute(
        select(func.count(StageAssignment.id)).where(
            StageAssignment.status.in_(
                [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
            ),
            StageAssignment.lease_expires_at < datetime.now(UTC),
        )
    )
    return result.scalar_one()


async def scheduler_throughput(session: AsyncSession, *, since: datetime | None = None) -> int:
    since = since or (datetime.now(UTC) - timedelta(minutes=5))
    result = await session.execute(
        select(func.count(JobSchedule.id)).where(
            JobSchedule.status == JobScheduleStatus.DONE, JobSchedule.updated_at >= since
        )
    )
    return result.scalar_one()
