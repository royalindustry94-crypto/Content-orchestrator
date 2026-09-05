from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import (
    get_membership,
    require_workspace_admin,
    require_workspace_member,
)
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.schemas.membership import MembershipCreate, MembershipOut, MembershipRoleUpdate

router = APIRouter(prefix="/workspaces/{workspace_id}/memberships", tags=["memberships"])


async def _admin_count(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count()).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.role == WorkspaceRole.ADMIN,
        )
    )
    return result.scalar_one()


@router.get("", response_model=list[MembershipOut])
async def list_memberships(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> list[WorkspaceMembership]:
    result = await db.execute(
        select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == workspace_id)
    )
    return list(result.scalars().all())


@router.post("", response_model=MembershipOut, status_code=status.HTTP_201_CREATED)
async def invite_member(
    request: Request,
    workspace_id: uuid.UUID,
    payload: MembershipCreate,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> WorkspaceMembership:
    existing = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == payload.user_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="user is already a member of this workspace",
        )

    membership = WorkspaceMembership(
        workspace_id=workspace_id, user_id=payload.user_id, role=payload.role
    )
    db.add(membership)
    await db.flush()
    audit(
        request,
        "workspace_member_invited",
        workspace_id=str(workspace_id),
        actor_user_id=str(_membership.user_id),
        target_user_id=str(payload.user_id),
        role=payload.role.value,
    )
    return membership


@router.patch("/{user_id}", response_model=MembershipOut)
async def update_member_role(
    request: Request,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    payload: MembershipRoleUpdate,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> WorkspaceMembership:
    target = await get_membership(workspace_id, AuthenticatedUser(id=str(user_id), email=None), db)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    if target.role == WorkspaceRole.ADMIN and payload.role != WorkspaceRole.ADMIN:
        if await _admin_count(db, workspace_id) <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="workspace must retain at least one admin",
            )

    previous_role = target.role
    target.role = payload.role
    await db.flush()
    audit(
        request,
        "workspace_member_role_changed",
        workspace_id=str(workspace_id),
        actor_user_id=str(_membership.user_id),
        target_user_id=str(user_id),
        previous_role=previous_role.value,
        new_role=payload.role.value,
    )
    return target


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    request: Request,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
):
    """Admins can remove anyone; any member can remove themselves
    (leave). Removing the workspace's last admin is rejected either way.
    """
    caller_membership = await get_membership(workspace_id, user, db)
    if caller_membership is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not a member")

    is_self_leave = str(user_id) == user.id
    if not is_self_leave and caller_membership.role != WorkspaceRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="requires one of: admin"
        )

    target = await get_membership(workspace_id, AuthenticatedUser(id=str(user_id), email=None), db)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="member not found")

    if target.role == WorkspaceRole.ADMIN and await _admin_count(db, workspace_id) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="workspace must retain at least one admin",
        )

    removed_role = target.role
    await db.delete(target)
    await db.commit()
    audit(
        request,
        "workspace_member_removed",
        workspace_id=str(workspace_id),
        actor_user_id=user.id,
        target_user_id=str(user_id),
        removed_role=removed_role.value,
        self_leave=is_self_leave,
    )
