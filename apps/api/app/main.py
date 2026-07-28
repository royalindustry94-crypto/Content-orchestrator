"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.concurrency import router as concurrency_router
from app.api.routes.content_jobs import router as content_jobs_router
from app.api.routes.health import router as health_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.review_gates import router as review_gates_router
from app.api.routes.spend import router as spend_router
from app.api.routes.workers import admin_router as workers_admin_router
from app.api.routes.workers import worker_router as workers_machine_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.audit import RequestIDMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.orchestration import consumers

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)
logger = logging.getLogger(__name__)

# Review approve/reject is bus-mediated; register once at import.
consumers.register_all()


@dataclass
class AutomationRuntimeState:
    """Process-local liveness for background automation loops."""

    started_at: datetime | None = None
    maintenance_ticks: int = 0
    maintenance_last_ok_at: datetime | None = None
    maintenance_last_error: str | None = None
    outbox_ticks: int = 0
    outbox_last_ok_at: datetime | None = None
    outbox_last_error: str | None = None
    scheduler_ticks: int = 0
    scheduler_last_ok_at: datetime | None = None
    scheduler_last_error: str | None = None
    scheduler_jobs_leased: int = 0
    tasks_running: list[str] = field(default_factory=list)


automation_state = AutomationRuntimeState()


async def _outbox_relay_loop() -> None:
    """Dispatch pending outbox events (including review decisions)."""
    from app.db.session import AsyncSessionLocal
    from app.orchestration import relay

    while True:
        await asyncio.sleep(settings.outbox_relay_interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                await relay.poll_and_dispatch(session)
                await session.commit()
            automation_state.outbox_ticks += 1
            automation_state.outbox_last_ok_at = datetime.now(UTC)
            automation_state.outbox_last_error = None
        except Exception as exc:  # noqa: BLE001 — tick must survive transient DB errors
            automation_state.outbox_last_error = str(exc)
            logger.exception("outbox relay tick failed")


async def _scheduler_loop() -> None:
    """Lease due job_schedule rows and dispatch stage work."""
    from app.db.session import AsyncSessionLocal
    from app.orchestration import scheduler

    while True:
        await asyncio.sleep(settings.scheduler_interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                leased = await scheduler.poll_and_lease(
                    session, batch_size=settings.scheduler_batch_size
                )
                for job in leased:
                    await scheduler.process_leased_job(session, job)
                reaped = await scheduler.reap_expired_leases(session)
                await session.commit()
            automation_state.scheduler_ticks += 1
            automation_state.scheduler_jobs_leased += len(leased)
            automation_state.scheduler_last_ok_at = datetime.now(UTC)
            automation_state.scheduler_last_error = None
            if leased or reaped:
                logger.info(
                    "scheduler tick",
                    extra={"leased": len(leased), "reaped": reaped},
                )
        except Exception as exc:  # noqa: BLE001
            automation_state.scheduler_last_error = str(exc)
            logger.exception("scheduler tick failed")


async def _orchestration_maintenance_loop() -> None:
    """Maintenance tick: offline sweep + lease reaping (WS3) and
    queue-depth back-pressure evaluation (WS4).
    """
    from app.db.session import AsyncSessionLocal
    from app.models.enums import RecoveryReason
    from app.orchestration.backpressure import evaluate_all_active_workspaces
    from app.orchestration.recovery import reap_expired_leases, reap_worker_assignments
    from app.services.workers import mark_stale_workers_offline

    while True:
        await asyncio.sleep(settings.assignment_reaper_interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                flipped = await mark_stale_workers_offline(
                    session, offline_after_seconds=settings.worker_offline_after_seconds
                )
                reaped_offline = 0
                for worker_id in flipped:
                    outcomes = await reap_worker_assignments(
                        session, worker_id, reason=RecoveryReason.WORKER_OFFLINE
                    )
                    reaped_offline += len(outcomes)
                expired = await reap_expired_leases(session)
                bp_snapshots = await evaluate_all_active_workspaces(session)
                await session.commit()
            automation_state.maintenance_ticks += 1
            automation_state.maintenance_last_ok_at = datetime.now(UTC)
            automation_state.maintenance_last_error = None
            bp_changed = sum(1 for s in bp_snapshots if s.changed)
            if flipped or expired or reaped_offline or bp_changed:
                logger.info(
                    "maintenance tick",
                    extra={
                        "workers_flipped": len(flipped),
                        "assignments_reaped_offline": reaped_offline,
                        "assignments_reaped_expired": len(expired),
                        "backpressure_transitions": bp_changed,
                    },
                )
        except Exception as exc:  # noqa: BLE001 — tick must survive transient DB errors
            automation_state.maintenance_last_error = str(exc)
            logger.exception("orchestration maintenance tick failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "service starting",
        extra={"service": settings.service_name, "environment": settings.environment},
    )
    background_tasks: list[asyncio.Task] = []
    automation_state.started_at = datetime.now(UTC)
    automation_state.tasks_running = []
    if settings.environment != "test":
        background_tasks.append(asyncio.create_task(_orchestration_maintenance_loop()))
        background_tasks.append(asyncio.create_task(_outbox_relay_loop()))
        background_tasks.append(asyncio.create_task(_scheduler_loop()))
        automation_state.tasks_running = ["maintenance", "outbox_relay", "scheduler"]
    app.state.automation = automation_state
    yield
    for task in background_tasks:
        task.cancel()
    if background_tasks:
        await asyncio.gather(*background_tasks, return_exceptions=True)
    automation_state.tasks_running = []
    logger.info("service shutting down", extra={"service": settings.service_name})


app = FastAPI(
    title="Content Orchestrator API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestIDMiddleware)

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(profiles_router)
app.include_router(workspaces_router)
app.include_router(memberships_router)
app.include_router(content_jobs_router)
app.include_router(review_gates_router)
app.include_router(spend_router)
app.include_router(concurrency_router)
app.include_router(workers_machine_router)
app.include_router(workers_admin_router)
