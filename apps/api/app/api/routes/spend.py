"""Workspace spend cap and usage API."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import require_workspace_admin, require_workspace_member
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.spend import SpendOut, SpendUpdateIn
from app.services import spend as spend_service

router = APIRouter(prefix="/workspaces/{workspace_id}/spend", tags=["spend"])


@router.get("", response_model=SpendOut)
async def get_spend(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> SpendOut:
    snap = await spend_service.spend_snapshot(db, workspace_id=workspace_id)
    return SpendOut(**snap)


@router.patch("", response_model=SpendOut)
async def update_spend(
    workspace_id: uuid.UUID,
    payload: SpendUpdateIn,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> SpendOut:
    if payload.daily_cap_usd is None and payload.monthly_cap_usd is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="at least one of daily_cap_usd or monthly_cap_usd is required",
        )
    if (
        payload.daily_cap_usd is not None
        and payload.monthly_cap_usd is not None
        and payload.daily_cap_usd > payload.monthly_cap_usd
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="daily_cap_usd cannot exceed monthly_cap_usd",
        )
    await spend_service.update_workspace_spend_cap(
        db,
        workspace_id=workspace_id,
        actor_id=uuid.UUID(user.id),
        daily_cap_usd=payload.daily_cap_usd,
        monthly_cap_usd=payload.monthly_cap_usd,
    )
    audit(
        request,
        "spend_cap_updated",
        workspace_id=str(workspace_id),
        daily_cap_usd=payload.daily_cap_usd,
        monthly_cap_usd=payload.monthly_cap_usd,
    )
    snap = await spend_service.spend_snapshot(db, workspace_id=workspace_id)
    return SpendOut(**snap)
