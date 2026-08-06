"""Workspace-scoped Operations Dashboard projections.

All values come from durable tables or deploy-injected metadata. Missing
deployment metadata is returned as unavailable rather than fabricated.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignments import StageAssignment
from app.models.billing import BillingWebhookEvent
from app.models.config import SpendCap
from app.models.delivery import PublishJob
from app.models.enums import (
    DeadLetterStatus,
    JobScheduleStatus,
    JobType,
    PipelineRunStatus,
    PublishJobStatus,
    ReviewGateStatus,
    StageAssignmentStatus,
    WebhookStatus,
    WorkerStatus,
)
from app.models.operations import DeadLetterJob, WebhookEvent
from app.models.pipeline import PipelineRun
from app.models.review_gate import ReviewGate
from app.models.scheduling import JobSchedule, WorkspaceConcurrencyLimit
from app.models.spend import SpendLog
from app.models.workers import WorkerRegistration
from app.models.workspace import Workspace
from app.schemas.operations_dashboard import (
    AlertsOut,
    DeploymentInfo,
    ExecutiveDashboardOut,
    OperationsAlert,
    PipelineMonitorOut,
    PipelineRow,
    WorkerMonitorOut,
    WorkerMonitorRow,
)
from app.services.workers import compute_liveness

logger = logging.getLogger(__name__)


def _enum_value(value: object) -> str:
    return str(value.value if hasattr(value, "value") else value)


def _deployment_info() -> DeploymentInfo:
    settings = get_settings()
    deployed_at = None
    if settings.deployment_at:
        try:
            deployed_at = datetime.fromisoformat(
                settings.deployment_at.replace("Z", "+00:00")
            )
        except ValueError:
            logger.warning(
                "operations_invalid_deployment_at",
                extra={"deployment_at": settings.deployment_at},
            )
    return DeploymentInfo(
        ci_status=(settings.deployment_ci_status or "unavailable").strip().lower(),
        ci_url=settings.deployment_ci_url,
        git_branch=settings.deployment_git_branch,
        commit_sha=settings.deployment_commit_sha,
        deployed_at=deployed_at,
    )


async def _count(session: AsyncSession, stmt) -> int:
    value = (await session.execute(stmt)).scalar_one()
    return int(value or 0)


async def _spend_totals(
    session: AsyncSession, workspace_id: uuid.UUID
) -> tuple[Decimal, Decimal]:
    now = datetime.now(UTC)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start.replace(day=1)
    row = (
        await session.execute(
            select(
                func.coalesce(
                    func.sum(SpendLog.cost_usd).filter(SpendLog.occurred_at >= day_start), 0
                ),
                func.coalesce(
                    func.sum(SpendLog.cost_usd).filter(
                        SpendLog.occurred_at >= month_start
                    ),
                    0,
                ),
            ).where(SpendLog.workspace_id == workspace_id)
        )
    ).one()
    return Decimal(str(row[0])), Decimal(str(row[1]))


async def executive(
    session: AsyncSession, workspace_id: uuid.UUID
) -> ExecutiveDashboardOut:
    active_assignments = [
        StageAssignmentStatus.DISPATCHED,
        StageAssignmentStatus.ACKNOWLEDGED,
    ]
    workers = await session.execute(
        select(WorkerRegistration.status, func.count(WorkerRegistration.id))
        .where(
            WorkerRegistration.deregistered_at.is_(None),
            or_(
                WorkerRegistration.workspace_id == workspace_id,
                WorkerRegistration.workspace_id.is_(None),
            ),
        )
        .group_by(WorkerRegistration.status)
    )
    worker_counts = {_enum_value(status): int(count) for status, count in workers.all()}
    jobs_running = await _count(
        session,
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.status.in_(active_assignments),
        ),
    )
    jobs_queued = await _count(
        session,
        select(func.count(JobSchedule.id)).where(
            JobSchedule.workspace_id == workspace_id,
            JobSchedule.status == JobScheduleStatus.PENDING,
        ),
    )
    jobs_failed = await _count(
        session,
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.status == StageAssignmentStatus.FAILED,
        ),
    )
    reviews = await _count(
        session,
        select(func.count(ReviewGate.id)).where(
            ReviewGate.workspace_id == workspace_id,
            ReviewGate.status == ReviewGateStatus.AWAITING,
        ),
    )
    spend_today, spend_month = await _spend_totals(session, workspace_id)
    workspace_exists = await _count(
        session,
        select(func.count(Workspace.id)).where(Workspace.id == workspace_id),
    )
    return ExecutiveDashboardOut(
        workers_online=worker_counts.get(WorkerStatus.ONLINE.value, 0),
        workers_busy=worker_counts.get(WorkerStatus.BUSY.value, 0),
        jobs_running=jobs_running,
        jobs_queued=jobs_queued,
        jobs_failed=jobs_failed,
        human_reviews_waiting=reviews,
        spend_today_usd=spend_today,
        spend_month_usd=spend_month,
        active_workspaces=workspace_exists,
        deployment=_deployment_info(),
        generated_at=datetime.now(UTC),
    )


async def workers(
    session: AsyncSession, workspace_id: uuid.UUID
) -> WorkerMonitorOut:
    settings = get_settings()
    result = await session.execute(
        select(WorkerRegistration)
        .where(
            WorkerRegistration.deregistered_at.is_(None),
            or_(
                WorkerRegistration.workspace_id == workspace_id,
                WorkerRegistration.workspace_id.is_(None),
            ),
        )
        .order_by(WorkerRegistration.name)
    )
    rows: list[WorkerMonitorRow] = []
    now = datetime.now(UTC)
    for worker in result.scalars().all():
        active = (
            await session.execute(
                select(StageAssignment)
                .where(
                    StageAssignment.workspace_id == workspace_id,
                    StageAssignment.worker_id == worker.id,
                    StageAssignment.status.in_(
                        [
                            StageAssignmentStatus.DISPATCHED,
                            StageAssignmentStatus.ACKNOWLEDGED,
                        ]
                    ),
                )
                .order_by(StageAssignment.updated_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        counts = await session.execute(
            select(StageAssignment.status, func.count(StageAssignment.id))
            .where(
                StageAssignment.workspace_id == workspace_id,
                StageAssignment.worker_id == worker.id,
            )
            .group_by(StageAssignment.status)
        )
        status_counts = {
            _enum_value(status): int(count) for status, count in counts.all()
        }
        retry_count = await _count(
            session,
            select(func.count(StageAssignment.id)).where(
                StageAssignment.workspace_id == workspace_id,
                StageAssignment.worker_id == worker.id,
                StageAssignment.attempt_number > 1,
            ),
        )
        queue = 0
        if worker.supported_stages:
            queue = await _count(
                session,
                select(func.count(StageAssignment.id)).where(
                    StageAssignment.workspace_id == workspace_id,
                    StageAssignment.status == StageAssignmentStatus.PENDING,
                    StageAssignment.stage.in_(worker.supported_stages),
                ),
            )
        lease_status = "none"
        if active is not None and active.lease_expires_at is not None:
            lease_status = "expired" if active.lease_expires_at <= now else "active"
        liveness = compute_liveness(
            worker.last_heartbeat_at,
            suspect_after_seconds=settings.worker_suspect_after_seconds,
            offline_after_seconds=settings.worker_offline_after_seconds,
        )
        display_status = (
            WorkerStatus.OFFLINE.value
            if liveness == "dead"
            else ("suspect" if liveness == "suspect" else _enum_value(worker.status))
        )
        rows.append(
            WorkerMonitorRow(
                id=worker.id,
                name=worker.name,
                status=display_status,
                current_job=(
                    f"{_enum_value(active.stage)} · {active.pipeline_run_id}"
                    if active is not None
                    else None
                ),
                queue=queue,
                last_heartbeat_at=worker.last_heartbeat_at,
                retry_count=retry_count,
                jobs_completed=status_counts.get(
                    StageAssignmentStatus.COMPLETED.value, 0
                ),
                jobs_failed=status_counts.get(StageAssignmentStatus.FAILED.value, 0),
                lease_status=lease_status,
            )
        )
    return WorkerMonitorOut(workers=rows, generated_at=datetime.now(UTC))


async def pipelines(
    session: AsyncSession, workspace_id: uuid.UUID
) -> PipelineMonitorOut:
    active_statuses = [
        PipelineRunStatus.CREATED,
        PipelineRunStatus.RUNNING,
        PipelineRunStatus.PAUSED,
        PipelineRunStatus.COMPENSATING,
    ]
    active = await _count(
        session,
        select(func.count(PipelineRun.id)).where(
            PipelineRun.workspace_id == workspace_id,
            PipelineRun.status.in_(active_statuses),
        ),
    )
    failed = await _count(
        session,
        select(func.count(PipelineRun.id)).where(
            PipelineRun.workspace_id == workspace_id,
            PipelineRun.status == PipelineRunStatus.FAILED,
        ),
    )
    queued = await _count(
        session,
        select(func.count(JobSchedule.id)).where(
            JobSchedule.workspace_id == workspace_id,
            JobSchedule.status == JobScheduleStatus.PENDING,
        ),
    )
    retrying = await _count(
        session,
        select(func.count(func.distinct(JobSchedule.ref_id))).where(
            JobSchedule.workspace_id == workspace_id,
            JobSchedule.job_type == JobType.RETRY,
            JobSchedule.status.in_(
                [JobScheduleStatus.PENDING, JobScheduleStatus.LEASED]
            ),
        ),
    )
    dlq = await _count(
        session,
        select(func.count(DeadLetterJob.id)).where(
            DeadLetterJob.workspace_id == workspace_id,
            DeadLetterJob.status == DeadLetterStatus.PENDING,
        ),
    )
    reviews = await _count(
        session,
        select(func.count(ReviewGate.id)).where(
            ReviewGate.workspace_id == workspace_id,
            ReviewGate.status == ReviewGateStatus.AWAITING,
        ),
    )
    publish_queue = await _count(
        session,
        select(func.count(PublishJob.id)).where(
            PublishJob.workspace_id == workspace_id,
            PublishJob.deleted_at.is_(None),
            PublishJob.status.in_(
                [PublishJobStatus.PENDING, PublishJobStatus.PUBLISHING]
            ),
        ),
    )
    result = await session.execute(
        select(PipelineRun)
        .where(
            PipelineRun.workspace_id == workspace_id,
            PipelineRun.status.in_(
                [*active_statuses, PipelineRunStatus.FAILED]
            ),
        )
        .order_by(PipelineRun.updated_at.desc())
        .limit(100)
    )
    rows = [
        PipelineRow(
            id=run.id,
            status=_enum_value(run.status),
            current_stage=_enum_value(run.current_stage),
            pause_reason=run.pause_reason,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )
        for run in result.scalars().all()
    ]
    return PipelineMonitorOut(
        active_pipelines=active,
        queue_depth=queued,
        failed_pipelines=failed,
        retrying_pipelines=retrying,
        dead_letter_queue=dlq,
        review_gates=reviews,
        publish_queue=publish_queue,
        pipelines=rows,
        generated_at=datetime.now(UTC),
    )


async def alerts(session: AsyncSession, workspace_id: uuid.UUID) -> AlertsOut:
    now = datetime.now(UTC)
    since = now - timedelta(days=1)
    items: list[OperationsAlert] = []

    worker_result = await session.execute(
        select(WorkerRegistration).where(
            WorkerRegistration.deregistered_at.is_(None),
            or_(
                WorkerRegistration.workspace_id == workspace_id,
                WorkerRegistration.workspace_id.is_(None),
            ),
        )
    )
    settings = get_settings()
    offline_count = sum(
        1
        for worker in worker_result.scalars().all()
        if compute_liveness(
            worker.last_heartbeat_at,
            suspect_after_seconds=settings.worker_suspect_after_seconds,
            offline_after_seconds=settings.worker_offline_after_seconds,
        )
        == "dead"
    )
    failed_jobs = await _count(
        session,
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.status == StageAssignmentStatus.FAILED,
            StageAssignment.updated_at >= since,
        ),
    )
    reviews = await _count(
        session,
        select(func.count(ReviewGate.id)).where(
            ReviewGate.workspace_id == workspace_id,
            ReviewGate.status == ReviewGateStatus.AWAITING,
        ),
    )
    queue = await _count(
        session,
        select(func.count(JobSchedule.id)).where(
            JobSchedule.workspace_id == workspace_id,
            JobSchedule.status == JobScheduleStatus.PENDING,
        ),
    )
    soft_limit = (
        await session.execute(
            select(WorkspaceConcurrencyLimit.queue_soft_limit).where(
                WorkspaceConcurrencyLimit.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none() or settings.queue_soft_limit_default
    failed_webhooks = await _count(
        session,
        select(func.count(WebhookEvent.id)).where(
            WebhookEvent.workspace_id == workspace_id,
            WebhookEvent.status == WebhookStatus.FAILED,
            WebhookEvent.updated_at >= since,
        ),
    )
    failed_webhooks += await _count(
        session,
        select(func.count(BillingWebhookEvent.id)).where(
            BillingWebhookEvent.workspace_id == workspace_id,
            BillingWebhookEvent.event_type == "invoice.payment_failed",
            BillingWebhookEvent.processed_at >= since,
        ),
    )
    spend_today, spend_month = await _spend_totals(session, workspace_id)
    cap = (
        await session.execute(
            select(SpendCap).where(
                SpendCap.workspace_id == workspace_id,
                SpendCap.provider.is_(None),
            )
        )
    ).scalar_one_or_none()
    spend_warning = False
    spend_message = "No workspace-wide spend cap configured"
    if cap is not None:
        daily_cap = Decimal(str(cap.daily_cap_usd))
        monthly_cap = Decimal(str(cap.monthly_cap_usd))
        spend_warning = (
            (daily_cap > 0 and spend_today >= daily_cap * Decimal("0.8"))
            or (monthly_cap > 0 and spend_month >= monthly_cap * Decimal("0.8"))
        )
        spend_message = (
            f"${spend_today:.4f} today / ${daily_cap:.4f} cap; "
            f"${spend_month:.4f} month / ${monthly_cap:.4f} cap"
        )

    def add(key: str, title: str, count: int, message: str, severity: str) -> None:
        if count > 0:
            items.append(
                OperationsAlert(
                    key=key,
                    severity=severity,
                    title=title,
                    count=count,
                    message=message,
                )
            )

    add(
        "worker_offline",
        "Worker Offline",
        offline_count,
        f"{offline_count} registered worker(s) are offline",
        "critical",
    )
    add(
        "failed_jobs",
        "Failed Jobs",
        failed_jobs,
        f"{failed_jobs} assignment(s) failed in the last 24 hours",
        "critical",
    )
    ci = _deployment_info()
    ci_failed = int(ci.ci_status not in {"success", "passing", "green", "unavailable"})
    add(
        "failed_ci",
        "Failed CI",
        ci_failed,
        f"Deployment CI status is {ci.ci_status}",
        "critical",
    )
    add(
        "spend_warning",
        "Spend Warning",
        int(spend_warning),
        spend_message,
        "warning",
    )
    add(
        "review_waiting",
        "Review Waiting",
        reviews,
        f"{reviews} Human Review Gate(s) are waiting",
        "warning",
    )
    add(
        "queue_backlog",
        "Queue Backlog",
        queue if queue >= soft_limit else 0,
        f"Queue depth {queue} reached soft limit {soft_limit}",
        "warning",
    )
    add(
        "failed_webhooks",
        "Failed Webhooks",
        failed_webhooks,
        f"{failed_webhooks} webhook failure(s) in the last 24 hours",
        "critical",
    )
    return AlertsOut(alerts=items, generated_at=now)
