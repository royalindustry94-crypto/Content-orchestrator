"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.concurrency import router as concurrency_router
from app.api.routes.content_jobs import router as content_jobs_router
from app.api.routes.health import router as health_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.review_gates import router as review_gates_router
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
        except Exception:  # noqa: BLE001 — tick must survive transient DB errors
            logger.exception("outbox relay tick failed")


async def _orchestration_maintenance_loop() -> None:
    """Maintenance tick: offline sweep + lease reaping (WS3) and
    queue-depth back-pressure evaluation (WS4). Multi-replica safe
    (SKIP LOCKED + idempotent UPDATEs). Ordering matters: offline flip
    and that worker's assignment reap share one transaction so we never
    leave load=0 with DISPATCHED holdings for a dead worker.
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
        except Exception:  # noqa: BLE001 — tick must survive transient DB errors
            logger.exception("orchestration maintenance tick failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "service starting",
        extra={"service": settings.service_name, "environment": settings.environment},
    )
    # Tests drive offline/reaper paths with a controlled clock; the
    # background tick would only add nondeterminism there.
    background_tasks: list[asyncio.Task] = []
    if settings.environment != "test":
        background_tasks.append(asyncio.create_task(_orchestration_maintenance_loop()))
        background_tasks.append(asyncio.create_task(_outbox_relay_loop()))
    yield
    for task in background_tasks:
        task.cancel()
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
app.include_router(profiles_router)
app.include_router(workspaces_router)
app.include_router(memberships_router)
app.include_router(content_jobs_router)
app.include_router(review_gates_router)
app.include_router(concurrency_router)
app.include_router(workers_machine_router)
app.include_router(workers_admin_router)
