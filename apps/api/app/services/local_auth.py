"""Local email/password auth that mints Supabase-shaped JWTs.

Used when AUTH_MODE=local (Private Beta / staging without an external
Supabase project). Production may set AUTH_MODE=supabase and disable
these routes — JWT verification remains identical either way.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from dataclasses import dataclass

from jwt import encode as jwt_encode
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.local_auth import LocalAuthCredential


class AuthError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AuthToken:
    access_token: str
    token_type: str
    expires_in: int
    user_id: uuid.UUID
    email: str


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 password hash (self-contained; no bcrypt backend drift)."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000
    ).hex()
    return f"pbkdf2_sha256$200000${salt}${digest}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algo, rounds_s, salt, digest = password_hash.split("$", 3)
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    try:
        rounds = int(rounds_s)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), rounds
    ).hex()
    return hmac.compare_digest(candidate, digest)


def mint_access_token(*, user_id: uuid.UUID, email: str, expires_in: int = 3600) -> str:
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "email": email,
        "aud": settings.supabase_jwt_audience,
        "exp": int(time.time()) + expires_in,
        "role": "authenticated",
        "iss": "content-orchestrator-local",
    }
    return jwt_encode(
        payload,
        settings.supabase_jwt_secret,
        algorithm=settings.supabase_jwt_algorithm,
    )


async def signup(
    session: AsyncSession, *, email: str, password: str, full_name: str | None = None
) -> AuthToken:
    settings = get_settings()
    if settings.auth_mode != "local":
        raise AuthError("auth_disabled", "local signup is disabled when AUTH_MODE!=local")
    normalized = email.strip().lower()
    if len(password) < 8:
        raise AuthError("weak_password", "password must be at least 8 characters")

    existing = (
        await session.execute(
            select(LocalAuthCredential).where(LocalAuthCredential.email == normalized)
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise AuthError("email_taken", "an account with this email already exists")

    user_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
        {"id": str(user_id), "email": normalized},
    )
    await session.execute(
        text(
            "INSERT INTO profiles (id, email, full_name) VALUES (:id, :email, :full_name) "
            "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email"
        ),
        {"id": str(user_id), "email": normalized, "full_name": full_name},
    )
    session.add(
        LocalAuthCredential(
            user_id=user_id,
            email=normalized,
            password_hash=hash_password(password),
        )
    )
    await session.flush()
    token = mint_access_token(user_id=user_id, email=normalized)
    return AuthToken(
        access_token=token,
        token_type="bearer",
        expires_in=3600,
        user_id=user_id,
        email=normalized,
    )


async def login(session: AsyncSession, *, email: str, password: str) -> AuthToken:
    settings = get_settings()
    if settings.auth_mode != "local":
        raise AuthError("auth_disabled", "local login is disabled when AUTH_MODE!=local")
    normalized = email.strip().lower()
    row = (
        await session.execute(
            select(LocalAuthCredential).where(LocalAuthCredential.email == normalized)
        )
    ).scalar_one_or_none()
    if row is None or not verify_password(password, row.password_hash):
        raise AuthError("invalid_credentials", "invalid email or password")
    token = mint_access_token(user_id=row.user_id, email=row.email)
    return AuthToken(
        access_token=token,
        token_type="bearer",
        expires_in=3600,
        user_id=row.user_id,
        email=row.email,
    )
