"""Health check endpoint.

Distinguishes liveness (process is up) from readiness (dependencies are
reachable) — a load balancer or orchestrator needs both, and collapsing
them into one always-200 endpoint hides real outages.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    """Process is running. Does not touch the database."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Process is running AND its dependencies (currently: Postgres) are reachable.

    Returns 503 (not 200 with an error body) on failure so load balancers
    and orchestrators treat it as a real readiness failure.
    """
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        logger.exception("readiness check failed: database unreachable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unreachable",
        ) from exc
    return {"status": "ok", "database": "reachable"}
