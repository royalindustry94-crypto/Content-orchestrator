"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.health import router as health_router
from app.api.routes.memberships import router as memberships_router
from app.api.routes.profiles import router as profiles_router
from app.api.routes.workspaces import router as workspaces_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(service_name=settings.service_name, level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "service starting",
        extra={"service": settings.service_name, "environment": settings.environment},
    )
    yield
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

app.include_router(health_router)
app.include_router(profiles_router)
app.include_router(workspaces_router)
app.include_router(memberships_router)
