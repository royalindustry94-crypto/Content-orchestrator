"""Admin concurrency limits, back-pressure state, and provider budgets (WS4)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import require_workspace_admin, require_workspace_member
from app.core.security import get_current_session
from app.db.session import AsyncSessionLocal
from app.models.assignments import StageAssignment
from app.models.backpressure import ProviderConcurrencyBudget, WorkspaceBackpressureState
from app.models.enums import BackpressureState, StageAssignmentStatus
from app.models.scheduling import WorkspaceConcurrencyLimit
from app.models.workspace_membership import WorkspaceMembership
from app.orchestration.backpressure import pending_depth
from app.schemas.concurrency import (
    ConcurrencyLimitsOut,
    ConcurrencyLimitsUpdate,
    ProviderBudgetOut,
    ProviderBudgetUpsert,
)

router = APIRouter(prefix="/workspaces/{workspace_id}", tags=["concurrency"])


@router.get("/concurrency", response_model=ConcurrencyLimitsOut)
async def get_concurrency(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> ConcurrencyLimitsOut:
    limit = (
        await db.execute(
            select(WorkspaceConcurrencyLimit).where(
                WorkspaceConcurrencyLimit.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    bp = (
        await db.execute(
            select(WorkspaceBackpressureState).where(
                WorkspaceBackpressureState.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    depth = await pending_depth(db, workspace_id)
    inflight = int(
        (
            await db.execute(
                select(func.count(StageAssignment.id)).where(
                    StageAssignment.workspace_id == workspace_id,
                    StageAssignment.status.in_(
                        [
                            StageAssignmentStatus.DISPATCHED,
                            StageAssignmentStatus.ACKNOWLEDGED,
                        ]
                    ),
                )
            )
        ).scalar_one()
        or 0
    )
    return ConcurrencyLimitsOut(
        workspace_id=workspace_id,
        max_concurrent_assignments=(limit.max_concurrent_assignments if limit is not None else 10),
        max_per_scheduler_tick=limit.max_per_scheduler_tick if limit is not None else 5,
        queue_soft_limit=limit.queue_soft_limit if limit is not None else 50,
        queue_hard_limit=limit.queue_hard_limit if limit is not None else 200,
        pending_depth=depth,
        in_flight=inflight,
        backpressure_state=(bp.state if bp is not None else BackpressureState.NORMAL),
    )


@router.put("/concurrency", response_model=ConcurrencyLimitsOut)
async def put_concurrency(
    workspace_id: uuid.UUID,
    payload: ConcurrencyLimitsUpdate,
    request: Request,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> ConcurrencyLimitsOut:
    if (
        payload.queue_soft_limit is not None
        and payload.queue_hard_limit is not None
        and payload.queue_hard_limit < payload.queue_soft_limit
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="queue_hard_limit must be >= queue_soft_limit",
        )

    limit = (
        await db.execute(
            select(WorkspaceConcurrencyLimit).where(
                WorkspaceConcurrencyLimit.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    if limit is None:
        soft = payload.queue_soft_limit if payload.queue_soft_limit is not None else 50
        hard = payload.queue_hard_limit if payload.queue_hard_limit is not None else 200
        if hard < soft:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="queue_hard_limit must be >= queue_soft_limit",
            )
        limit = WorkspaceConcurrencyLimit(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            max_concurrent_assignments=(
                payload.max_concurrent_assignments
                if payload.max_concurrent_assignments is not None
                else 10
            ),
            max_per_scheduler_tick=(
                payload.max_per_scheduler_tick if payload.max_per_scheduler_tick is not None else 5
            ),
            queue_soft_limit=soft,
            queue_hard_limit=hard,
        )
        db.add(limit)
    else:
        if payload.max_concurrent_assignments is not None:
            limit.max_concurrent_assignments = payload.max_concurrent_assignments
        if payload.max_per_scheduler_tick is not None:
            limit.max_per_scheduler_tick = payload.max_per_scheduler_tick
        if payload.queue_soft_limit is not None:
            limit.queue_soft_limit = payload.queue_soft_limit
        if payload.queue_hard_limit is not None:
            limit.queue_hard_limit = payload.queue_hard_limit
        if limit.queue_hard_limit < limit.queue_soft_limit:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="queue_hard_limit must be >= queue_soft_limit",
            )

    await db.flush()
    audit(
        request,
        "concurrency_limits_updated",
        workspace_id=str(workspace_id),
        max_concurrent_assignments=limit.max_concurrent_assignments,
        max_per_scheduler_tick=limit.max_per_scheduler_tick,
        queue_soft_limit=limit.queue_soft_limit,
        queue_hard_limit=limit.queue_hard_limit,
    )
    return await get_concurrency(workspace_id, db, _membership)


@router.get("/provider-budgets", response_model=list[ProviderBudgetOut])
async def list_provider_budgets(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> list[ProviderConcurrencyBudget]:
    result = await db.execute(
        select(ProviderConcurrencyBudget)
        .where(ProviderConcurrencyBudget.workspace_id == workspace_id)
        .order_by(ProviderConcurrencyBudget.provider.asc())
    )
    return list(result.scalars().all())


@router.put("/provider-budgets/{provider}", response_model=ProviderBudgetOut)
async def upsert_provider_budget(
    workspace_id: uuid.UUID,
    provider: str,
    payload: ProviderBudgetUpsert,
    request: Request,
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> ProviderBudgetOut:
    # FORCE RLS + no runtime write grants: mutate via service-role after admin guard.
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(
                select(ProviderConcurrencyBudget).where(
                    ProviderConcurrencyBudget.workspace_id == workspace_id,
                    ProviderConcurrencyBudget.provider == provider,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            existing = ProviderConcurrencyBudget(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                provider=provider,
                max_concurrent=payload.max_concurrent,
            )
            session.add(existing)
        else:
            existing.max_concurrent = payload.max_concurrent
        await session.commit()
        await session.refresh(existing)
        out = ProviderBudgetOut.model_validate(existing)
    audit(
        request,
        "provider_budget_upserted",
        workspace_id=str(workspace_id),
        provider=provider,
        max_concurrent=payload.max_concurrent,
    )
    return out


@router.delete(
    "/provider-budgets/{provider}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_provider_budget(
    workspace_id: uuid.UUID,
    provider: str,
    request: Request,
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> Response:
    async with AsyncSessionLocal() as session:
        existing = (
            await session.execute(
                select(ProviderConcurrencyBudget).where(
                    ProviderConcurrencyBudget.workspace_id == workspace_id,
                    ProviderConcurrencyBudget.provider == provider,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="provider budget not found",
            )
        await session.delete(existing)
        await session.commit()
    audit(
        request,
        "provider_budget_deleted",
        workspace_id=str(workspace_id),
        provider=provider,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
