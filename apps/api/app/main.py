"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.workers import admin_router as workers_admin_router
from app.api.routes.workers import worker_router as workers_machine_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.audit import RequestIDMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)
logger = logging.getLogger(__name__)


async def _offline_sweep_loop() -> None:
    """Server-driven offline detection (WS1): periodically flip workers
    with stale heartbeats to OFFLINE. Runs in-process; multiple API
    replicas running it concurrently is safe (idempotent single-statement
    UPDATE, row locks serialize)."""
    from app.db.session import AsyncSessionLocal
    from app.services.workers import mark_stale_workers_offline

    while True:
        await asyncio.sleep(settings.worker_offline_sweep_interval_seconds)
        try:
            async with AsyncSessionLocal() as session:
                flipped = await mark_stale_workers_offline(
                    session, offline_after_seconds=settings.worker_offline_after_seconds
                )
                await session.commit()
            if flipped:
                logger.info("offline sweep flipped workers", extra={"count": flipped})
        except Exception:  # noqa: BLE001 — sweep must survive transient DB errors
            logger.exception("offline sweep iteration failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "service starting",
        extra={"service": settings.service_name, "environment": settings.environment},
    )
    # Tests call mark_stale_workers_offline directly with a controlled
    # clock; the background sweep would only add nondeterminism there.
    sweep_task = (
        asyncio.create_task(_offline_sweep_loop()) if settings.environment != "test" else None
    )
    yield
    if sweep_task is not None:
        sweep_task.cancel()
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
app.include_router(workers_machine_router)
app.include_router(workers_admin_router)
