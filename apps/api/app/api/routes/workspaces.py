from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import (
    require_workspace_admin,
    require_workspace_content_author,
    require_workspace_member,
)
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.content_profile import WorkspaceContentProfile
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.schemas.workspace import (
    ContentProfileInput,
    ContentProfileOut,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from app.services.spend import ensure_default_spend_cap

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    payload: WorkspaceCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> Workspace:
    """Creates the workspace and makes the creator its sole admin in the
    same transaction — there is no code path that produces a workspace
    with zero admins.
    """
    workspace = Workspace(name=payload.name, created_by=uuid.UUID(user.id))
    db.add(workspace)
    await db.flush()  # assigns workspace.id without committing yet

    membership = WorkspaceMembership(
        workspace_id=workspace.id,
        user_id=uuid.UUID(user.id),
        role=WorkspaceRole.ADMIN,
    )
    db.add(membership)
    # Membership must be visible to RLS helpers before seeding spend_caps.
    await db.flush()
    await ensure_default_spend_cap(db, workspace_id=workspace.id, actor_id=uuid.UUID(user.id))
    await db.flush()
    return workspace


@router.get("", response_model=list[WorkspaceOut])
async def list_my_workspaces(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> list[Workspace]:
    # RLS already restricts this to workspaces the caller is a member of;
    # the join here is for correctness of ordering/filtering, not as the
    # sole access control.
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMembership, WorkspaceMembership.workspace_id == Workspace.id)
        .where(WorkspaceMembership.user_id == uuid.UUID(user.id))
        .order_by(Workspace.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found")
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    workspace_id: uuid.UUID,
    payload: WorkspaceUpdate,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> Workspace:
    workspace = await db.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="workspace not found")
    if payload.name is None and payload.priority_tier is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="at least one of name or priority_tier is required",
        )
    if payload.name is not None:
        workspace.name = payload.name
    if payload.priority_tier is not None:
        workspace.priority_tier = payload.priority_tier
    await db.flush()
    return workspace


@router.get("/{workspace_id}/content-profile", response_model=ContentProfileOut | None)
async def get_content_profile(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> WorkspaceContentProfile | None:
    """Return reusable content defaults, or null until setup is complete."""
    return await db.get(WorkspaceContentProfile, workspace_id)


@router.put("/{workspace_id}/content-profile", response_model=ContentProfileOut)
async def save_content_profile(
    workspace_id: uuid.UUID,
    payload: ContentProfileInput,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> WorkspaceContentProfile:
    """Create or replace the workspace's durable five-step content setup."""
    actor_id = uuid.UUID(user.id)
    profile = await db.get(WorkspaceContentProfile, workspace_id)
    values = payload.model_dump()
    if profile is None:
        profile = WorkspaceContentProfile(
            workspace_id=workspace_id,
            created_by=actor_id,
            updated_by=actor_id,
            **values,
        )
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)
        profile.updated_by = actor_id
    await db.flush()
    audit(
        request,
        "workspace_content_profile_saved",
        workspace_id=str(workspace_id),
        service_mode=profile.service_mode,
    )
    return profile
