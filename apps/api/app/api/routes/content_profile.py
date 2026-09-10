"""Workspace content profile — durable business/audience/brand-voice
defaults, set via the guided setup wizard or edited directly (Settings).

Onboarding gap closure (2026-09-09): previously nothing beyond workspace
name and spend caps was configurable for a new workspace. See migration
0055 for the full rationale. Uses the RLS-scoped runtime session, like
every other tenant route (`content_jobs.py`, `workspaces.py`).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import require_workspace_content_author, require_workspace_member
from app.core.security import get_current_session
from app.models.content_profile import WorkspaceContentProfile
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.workspace import ContentProfileInput, ContentProfileOut

router = APIRouter(prefix="/workspaces/{workspace_id}/content-profile", tags=["workspaces"])


async def _get_profile(db: AsyncSession, workspace_id: uuid.UUID) -> WorkspaceContentProfile | None:
    result = await db.execute(
        select(WorkspaceContentProfile).where(WorkspaceContentProfile.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


@router.get("", response_model=ContentProfileOut | None)
async def get_content_profile(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> WorkspaceContentProfile | None:
    """Null until the workspace has saved a profile at least once — not
    an error, and not a fabricated default.
    """
    return await _get_profile(db, workspace_id)


@router.put("", response_model=ContentProfileOut)
async def save_content_profile(
    workspace_id: uuid.UUID,
    payload: ContentProfileInput,
    request: Request,
    db: AsyncSession = Depends(get_current_session),
    membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> WorkspaceContentProfile:
    """Upsert: the guided wizard and manual Settings editing both call
    this. A field omitted/blank is cleared, not left stale — the caller
    always sends the full current form state.
    """
    profile = await _get_profile(db, workspace_id)
    fields = payload.model_dump()
    if profile is None:
        profile = WorkspaceContentProfile(
            workspace_id=workspace_id,
            created_by=membership.user_id,
            updated_by=membership.user_id,
            **fields,
        )
        db.add(profile)
    else:
        for key, value in fields.items():
            setattr(profile, key, value)
        profile.updated_by = membership.user_id
    await db.flush()
    audit(
        request,
        "workspace_content_profile_saved",
        workspace_id=str(workspace_id),
        actor_id=str(membership.user_id),
    )
    return profile
