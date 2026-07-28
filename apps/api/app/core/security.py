"""Supabase JWT verification.

FastAPI verifies the JWT Supabase Auth issued; it never issues, refreshes,
or stores tokens itself. See docs/milestone-2-identity-and-access.md §1.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError
from jwt import decode as jwt_decode
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import rls_scoped_session

settings = get_settings()

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Verified identity derived from a Supabase JWT's claims. Not a
    database row — callers that need the profile row query for it
    separately, keyed by `id`.
    """

    id: str  # Supabase auth.users.id / profiles.id (uuid as string)
    email: str | None


def _decode_supabase_jwt(token: str) -> dict:
    try:
        return jwt_decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=[settings.supabase_jwt_algorithm],
            audience=settings.supabase_jwt_audience,
        )
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    claims = _decode_supabase_jwt(credentials.credentials)

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token missing 'sub' claim",
        )

    return AuthenticatedUser(id=sub, email=claims.get("email"))


async def get_current_session(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AsyncGenerator[AsyncSession, None]:
    """RLS-scoped DB session for the authenticated caller. Every route
    that touches application data should depend on this (or on
    `app.core.authorization`'s guards, which depend on this) rather than
    on `app.db.session.get_db` directly.
    """
    async with rls_scoped_session(user.id) as session:
        yield session
