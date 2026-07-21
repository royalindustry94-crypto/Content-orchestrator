from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.profile import Profile
from app.schemas.profile import ProfileOut

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileOut)
async def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> Profile:
    """The `auth.users` trigger (see the Milestone 2 migration) creates
    the profiles row on signup, so this is normally a straight read. If
    it's missing anyway — trigger not yet caught up, or a user created
    before the trigger existed — self-heal by inserting it rather than
    500ing on a verified, legitimate caller.
    """
    profile = await db.get(Profile, uuid.UUID(user.id))
    if profile is None:
        profile = Profile(id=uuid.UUID(user.id), email=user.email or "")
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile
