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
# Content authors (Private Beta desk submit).
require_workspace_content_author = require_workspace_role(WorkspaceRole.ADMIN, WorkspaceRole.EDITOR)
# Human Review Gate decision-makers (matches review_decisions RLS insert roles).
#
# ADMIN is deliberately in both this set and require_workspace_content_author,
# so a solo Admin can author a draft and approve it themselves. This is an
# intentional product decision for the current Private Beta target market
# (docs/ROADMAP.md: solo operators / small agencies, "Founder-led onboarding
# for agencies") — the Human Review Gate's non-negotiable guarantee is that
# unreviewed content cannot auto-publish, not that the reviewer is a second
# human distinct from the author. A workspace that wants maker-checker
# separation today can enforce it operationally by not granting one person
# both roles' worth of trust — i.e. keep the Admin as owner-only and add
# separate Editor/Reviewer members. Revisit this default (e.g. block
# reviewer_id == content.created_by, or a workspace-level setting) if/when
# the product moves toward larger teams where that guarantee needs to be
# structural rather than operational. See docs/TECHNICAL_DEBT_REGISTER.md.
require_workspace_reviewer = require_workspace_role(WorkspaceRole.ADMIN, WorkspaceRole.REVIEWER)
