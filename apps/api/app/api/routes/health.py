"""Health check endpoint.

Distinguishes liveness (process is up) from readiness (dependencies are
reachable) — a load balancer or orchestrator needs both, and collapsing
them into one always-200 endpoint hides real outages.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.providers import provider_status

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/pipeline/provider")
async def pipeline_provider() -> dict:
    """Which provider backs the content pipeline, for honest UI labelling.

    Deployment configuration only — no workspace data — so this is
    unauthenticated for the same reason ``/auth/mode`` is: clients need to
    render the right thing regardless of session state, and operators need to
    confirm which mode an environment is actually running in.
    """
    return provider_status()


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


# Work that only the background loops perform. On a runtime that cannot host
# them these are genuinely not happening, and saying so is the point of this
# endpoint — an operator must never infer background progress that is absent.
_LOOP_ONLY_CAPABILITIES = (
    "draft_desk_stage_dispatch",
    "worker_liveness_sweep",
    "assignment_lease_recovery",
    "queue_backpressure_evaluation",
    "outbox_catch_up_delivery",
)

# Work that completes inside the request that triggers it, and therefore still
# holds when the loops are absent.
_REQUEST_INLINE_CAPABILITIES = (
    "auth",
    "workspace_management",
    "research_strategy_content_production_compliance_stages",
    "independent_auditors",
    "human_review_gate_open_and_decide",
    "spend_reservation_and_commit",
)


@router.get("/health/automation")
async def automation_health(request: Request) -> dict:
    """Expose background-loop liveness for ops (scheduler / outbox / maintenance).

    Loops are intentionally not started in ENVIRONMENT=test (tests drive the
    reapers directly) or under RUNTIME_PROFILE=serverless (a frozen process
    cannot tick one). Both cases report ``disabled`` with the reason and the
    capabilities that are consequently unavailable, rather than ``idle``, which
    would read as a transient stall of loops that were expected to run.
    """
    # Prefer lifespan-bound state; fall back to module singleton so tests
    # (ASGITransport without lifespan) still see a stable schema.
    from app.main import automation_state as module_state

    settings = get_settings()
    state = getattr(request.app.state, "automation", None) or module_state
    if state.tasks_running:
        loop_status = "ok"
    elif not settings.background_loops_supported:
        loop_status = "disabled"
    else:
        loop_status = "idle"
    return {
        "status": loop_status,
        "runtime_profile": settings.runtime_profile,
        "disabled_reason": settings.background_loops_disabled_reason,
        "unavailable_capabilities": (
            [] if settings.background_loops_supported else list(_LOOP_ONLY_CAPABILITIES)
        ),
        "request_inline_capabilities": list(_REQUEST_INLINE_CAPABILITIES),
        "started_at": state.started_at.isoformat() if state.started_at else None,
        "tasks_running": list(state.tasks_running),
        "maintenance": {
            "ticks": state.maintenance_ticks,
            "last_ok_at": (
                state.maintenance_last_ok_at.isoformat()
                if state.maintenance_last_ok_at
                else None
            ),
            "last_error": state.maintenance_last_error,
        },
        "outbox_relay": {
            "ticks": state.outbox_ticks,
            "last_ok_at": (
                state.outbox_last_ok_at.isoformat() if state.outbox_last_ok_at else None
            ),
            "last_error": state.outbox_last_error,
        },
        "scheduler": {
            "ticks": state.scheduler_ticks,
            "jobs_leased": state.scheduler_jobs_leased,
            "last_ok_at": (
                state.scheduler_last_ok_at.isoformat() if state.scheduler_last_ok_at else None
            ),
            "last_error": state.scheduler_last_error,
        },
    }
