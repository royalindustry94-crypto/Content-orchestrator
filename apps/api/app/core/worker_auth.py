"""Machine authentication for worker endpoints (WS1 design amendment 1).

Each worker authenticates with `Authorization: Bearer <credential_id>.<secret>`.
The credential identifies an individual worker (not "a worker"), and the
secret is verified in constant time against its SHA-256 hash at rest.

Why SHA-256 and not bcrypt: the secret is a server-generated 256-bit
random token (`secrets.token_urlsafe(32)`), not a human password — brute
force against the hash is already infeasible, and worker auth runs on
every heartbeat, so a deliberately-slow KDF would only add latency
without adding security.

Clock-skew assumption: credential expiry (`expires_at`) is evaluated
against the API server's clock only. Worker clocks are never consulted
anywhere in the protocol (heartbeat timestamps are server-assigned too),
so the maximum tolerated worker clock skew is unbounded by design; the
only clock that matters is the database/API host clock.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.enums import WorkerCredentialStatus
from app.models.workers import WorkerCredential

_bearer_scheme = HTTPBearer(auto_error=False)

# Compared against when the credential id doesn't exist, so the
# request-duration profile is the same for "unknown id" and "bad secret".
_DUMMY_HASH = hashlib.sha256(b"nonexistent-credential-dummy").hexdigest()


def hash_worker_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def generate_worker_secret() -> str:
    return secrets.token_urlsafe(32)


@dataclass(frozen=True)
class AuthenticatedWorker:
    worker_id: uuid.UUID
    credential_id: uuid.UUID
    workspace_id: uuid.UUID


def _unauthorized() -> HTTPException:
    # One indistinguishable error for every failure mode (missing,
    # malformed, unknown, revoked, expired, wrong secret) — the response
    # must not help an attacker enumerate credential ids or states.
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="invalid worker credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_worker(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthenticatedWorker:
    if credentials is None:
        raise _unauthorized()

    token = credentials.credentials
    credential_id_raw, sep, secret = token.partition(".")
    if not sep or not secret:
        raise _unauthorized()
    try:
        credential_id = uuid.UUID(credential_id_raw)
    except ValueError:
        raise _unauthorized() from None

    async with AsyncSessionLocal() as session:  # service role: credentials are RLS-hidden
        result = await session.execute(
            select(WorkerCredential).where(WorkerCredential.id == credential_id)
        )
        credential = result.scalar_one_or_none()

    stored_hash = credential.secret_hash if credential is not None else _DUMMY_HASH
    secret_ok = hmac.compare_digest(hash_worker_secret(secret), stored_hash)

    if credential is None or not secret_ok:
        raise _unauthorized()
    if credential.status != WorkerCredentialStatus.ACTIVE:
        raise _unauthorized()
    if credential.expires_at is not None and credential.expires_at <= datetime.now(UTC):
        raise _unauthorized()

    return AuthenticatedWorker(
        worker_id=credential.worker_id,
        credential_id=credential.id,
        workspace_id=credential.workspace_id,
    )
