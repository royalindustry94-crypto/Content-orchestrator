"""Local auth routes (AUTH_MODE=local)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db
from app.schemas.auth import AuthTokenOut, LoginIn, SignupIn
from app.services import local_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _ensure_local_auth_enabled() -> None:
    if get_settings().auth_mode != "local":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="local auth is disabled",
        )


@router.post("/signup", response_model=AuthTokenOut, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupIn, db: AsyncSession = Depends(get_db)) -> AuthTokenOut:
    _ensure_local_auth_enabled()
    try:
        token = await local_auth.signup(
            db,
            email=str(payload.email),
            password=payload.password,
            full_name=payload.full_name,
        )
    except local_auth.AuthError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code == "email_taken"
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc
    await db.commit()
    return AuthTokenOut(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user_id=token.user_id,
        email=token.email,
    )


@router.post("/login", response_model=AuthTokenOut)
async def login(payload: LoginIn, db: AsyncSession = Depends(get_db)) -> AuthTokenOut:
    _ensure_local_auth_enabled()
    try:
        token = await local_auth.login(
            db, email=str(payload.email), password=payload.password
        )
    except local_auth.AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        ) from exc
    return AuthTokenOut(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user_id=token.user_id,
        email=token.email,
    )


@router.get("/mode")
async def auth_mode() -> dict[str, str]:
    return {"auth_mode": get_settings().auth_mode}
