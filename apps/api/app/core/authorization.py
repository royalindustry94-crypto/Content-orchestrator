"""Workspace authorization guards.

These are the primary enforcement mechanism ("backend enforcement is
required; frontend checks are not sufficient" — project instructions).
Row Level Security (see the Milestone 2 migration) is the backstop behind
these, not a replacement for them — a guard here should reject an
unauthorized request before a query is even attempted.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole


async def get_membership(
    workspace_id: uuid.UUID,
    user: AuthenticatedUser,
    db: AsyncSession,
) -> WorkspaceMembership | None:
    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == uuid.UUID(user.id),
        )
    )
    return result.scalar_one_or_none()


def require_workspace_member():
    """Any role — used for read endpoints."""

    async def guard(
        workspace_id: uuid.UUID = Path(...),
        user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_current_session),
    ) -> WorkspaceMembership:
        membership = await get_membership(workspace_id, user, db)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not a member of this workspace",
            )
        return membership

    return guard


def require_workspace_role(*allowed_roles: WorkspaceRole):
    """Membership AND role in `allowed_roles` — used for write endpoints."""

    async def guard(
        workspace_id: uuid.UUID = Path(...),
        user: AuthenticatedUser = Depends(get_current_user),
        db: AsyncSession = Depends(get_current_session),
    ) -> WorkspaceMembership:
        membership = await get_membership(workspace_id, user, db)
        if membership is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="not a member of this workspace",
            )
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"requires one of: {', '.join(r.value for r in allowed_roles)}",
            )
        return membership

    return guard


require_workspace_admin = require_workspace_role(WorkspaceRole.ADMIN)
