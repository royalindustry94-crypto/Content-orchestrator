"""Worker registry endpoints (Workstream 1).

Two principals, two routers:

- `worker_router` — machine endpoints (`/workers/...`) authenticated by a
  per-worker credential (see app.core.worker_auth). The credential IS the
  identity: there is no worker id in these paths, so a worker can never
  act on another worker's row (no confused-deputy surface). Writes use
  the service-role session — workers are not tenants and RLS user
  policies deny registry writes by design.

- `admin_router` — user endpoints under `/workspaces/{workspace_id}/workers`,
  authenticated by the normal Supabase JWT with workspace guards. Reads
  go through the RLS session (policies are the backstop); credential and
  drain mutations are guard-checked and then applied via the service-role
  session because user roles have no write policies on these tables.

Every domain action emits a structured audit event (app.core.audit).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import require_workspace_admin, require_workspace_member
from app.core.config import get_settings
from app.core.security import get_current_session
from app.core.worker_auth import (
    AuthenticatedWorker,
    generate_worker_secret,
    get_current_worker,
    hash_worker_secret,
)
from app.db.session import AsyncSessionLocal
from app.models.enums import WorkerCredentialStatus, WorkerStatus
from app.models.workers import WorkerCredential, WorkerHeartbeat, WorkerRegistration
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.workers import (
    CredentialRotateOut,
    HeartbeatRecordOut,
    WorkerDrainIn,
    WorkerHeartbeatIn,
    WorkerOut,
    WorkerProvisionIn,
    WorkerProvisionOut,
    WorkerRegisterIn,
    WorkerRegisterOut,
)
from app.services.workers import compute_liveness

settings = get_settings()

worker_router = APIRouter(prefix="/workers", tags=["workers-machine"])
admin_router = APIRouter(prefix="/workspaces/{workspace_id}/workers", tags=["workers-admin"])


def _worker_out(registration: WorkerRegistration) -> WorkerOut:
    return WorkerOut(
        id=registration.id,
        workspace_id=registration.workspace_id,
        name=registration.name,
        status=registration.status,
        liveness=compute_liveness(
            registration.last_heartbeat_at,
            suspect_after_seconds=settings.worker_suspect_after_seconds,
            offline_after_seconds=settings.worker_offline_after_seconds,
        ),
        drain=registration.drain,
        supported_stages=registration.supported_stages,
        capabilities=registration.capabilities,
        worker_version=registration.worker_version,
        max_concurrency=registration.max_concurrency,
        current_load=registration.current_load,
        health_score=registration.health_score,
        last_heartbeat_at=registration.last_heartbeat_at,
        registered_at=registration.registered_at,
        deregistered_at=registration.deregistered_at,
    )


# --------------------------------------------------------------------------
# Machine endpoints (per-worker credential auth)
# --------------------------------------------------------------------------


@worker_router.post("/register", response_model=WorkerRegisterOut)
async def register_worker(
    payload: WorkerRegisterIn,
    request: Request,
    worker: AuthenticatedWorker = Depends(get_current_worker),
) -> WorkerRegisterOut:
    """Idempotent: repeat registration updates the same row (the worker
    row was created at provisioning; registration announces runtime
    facts). Revives a deregistered row. Does NOT clear an admin-set
    `drain` flag — drain is admin intent, not worker state.
    """
    if payload.capabilities.protocol_version not in settings.worker_capability_protocol_versions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "unsupported capability protocol_version "
                f"{payload.capabilities.protocol_version}; server accepts "
                f"{settings.worker_capability_protocol_versions}"
            ),
        )
    async with AsyncSessionLocal() as session:
        registration = await session.get(
            WorkerRegistration, worker.worker_id, with_for_update=True
        )
        if registration is None:  # credential FK guarantees existence; defensive
            raise HTTPException(status_code=404, detail="worker not found")
        now = datetime.now(UTC)
        registration.supported_stages = payload.supported_stages
        registration.capabilities = payload.capabilities.model_dump()
        registration.worker_version = payload.worker_version
        registration.max_concurrency = payload.max_concurrency
        registration.current_load = 0
        registration.status = WorkerStatus.ONLINE
        registration.last_heartbeat_at = now
        registration.registered_at = now
        registration.deregistered_at = None
        await session.commit()
    audit(
        request,
        "worker_registered",
        worker_id=str(worker.worker_id),
        credential_id=str(worker.credential_id),
        protocol_version=payload.capabilities.protocol_version,
        worker_version=payload.worker_version,
    )
    return WorkerRegisterOut(
        worker_id=worker.worker_id,
        status=WorkerStatus.ONLINE,
        accepted_protocol_version=payload.capabilities.protocol_version,
    )


@worker_router.post("/heartbeat", response_model=WorkerOut)
async def worker_heartbeat(
    payload: WorkerHeartbeatIn,
    request: Request,
    worker: AuthenticatedWorker = Depends(get_current_worker),
) -> WorkerOut:
    """Duplicate-delivery tolerant: the registry update is idempotent for
    identical payloads and heartbeat history is append-only, so a
    replayed heartbeat adds one harmless history row and changes nothing
    else. `heartbeat_at` is server-assigned — client clocks are never
    consulted (see clock-skew note in app.core.worker_auth).
    """
    if payload.status not in (WorkerStatus.ONLINE, WorkerStatus.BUSY, WorkerStatus.DRAINING):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="a heartbeat may report online, busy, or draining — not offline",
        )
    async with AsyncSessionLocal() as session:
        registration = await session.get(
            WorkerRegistration, worker.worker_id, with_for_update=True
        )
        if registration is None:
            raise HTTPException(status_code=404, detail="worker not found")
        if registration.deregistered_at is not None:
            raise HTTPException(
                status_code=status.HTTP_410_GONE, detail="worker is deregistered"
            )
        if payload.current_load > registration.max_concurrency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="current_load exceeds max_concurrency",
            )
        now = datetime.now(UTC)
        registration.status = payload.status
        registration.current_load = payload.current_load
        registration.last_heartbeat_at = now
        session.add(
            WorkerHeartbeat(
                worker_id=worker.worker_id,
                status=payload.status,
                current_load=payload.current_load,
                heartbeat_at=now,
            )
        )
        await session.commit()
        await session.refresh(registration)
        out = _worker_out(registration)
    audit(
        request,
        "worker_heartbeat",
        worker_id=str(worker.worker_id),
        status=payload.status.value,
        current_load=payload.current_load,
    )
    return out


@worker_router.post("/deregister", response_model=WorkerOut)
async def deregister_worker(
    request: Request,
    worker: AuthenticatedWorker = Depends(get_current_worker),
) -> WorkerOut:
    """Soft deregistration; idempotent (repeat returns the same terminal
    state). The row is retained for audit and heartbeat-history FKs;
    re-registration revives it.
    """
    async with AsyncSessionLocal() as session:
        registration = await session.get(
            WorkerRegistration, worker.worker_id, with_for_update=True
        )
        if registration is None:
            raise HTTPException(status_code=404, detail="worker not found")
        if registration.deregistered_at is None:
            registration.status = WorkerStatus.OFFLINE
            registration.current_load = 0
            registration.deregistered_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(registration)
        out = _worker_out(registration)
    audit(request, "worker_deregistered", worker_id=str(worker.worker_id))
    return out


# --------------------------------------------------------------------------
# Admin/user endpoints (JWT auth + workspace guards, RLS backstop)
# --------------------------------------------------------------------------


@admin_router.post("", response_model=WorkerProvisionOut, status_code=status.HTTP_201_CREATED)
async def provision_worker(
    workspace_id: uuid.UUID,
    payload: WorkerProvisionIn,
    request: Request,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> WorkerProvisionOut:
    """Creates a workspace-pinned worker identity plus its first
    credential. The plaintext secret appears in this response only and is
    stored exclusively as a SHA-256 hash. Global (unpinned) workers are
    not provisionable through the API in WS1 — that requires a platform
    operator role which does not exist yet.
    """
    secret = generate_worker_secret()
    async with AsyncSessionLocal() as session:
        registration = WorkerRegistration(
            workspace_id=workspace_id,
            name=payload.name,
            supported_stages=payload.supported_stages,
            capabilities=None,
            status=WorkerStatus.OFFLINE,
            max_concurrency=payload.max_concurrency,
            current_load=0,
            health_score=100,
            last_heartbeat_at=None,
            registered_at=datetime.now(UTC),
        )
        session.add(registration)
        await session.flush()
        credential = WorkerCredential(
            worker_id=registration.id,
            workspace_id=workspace_id,
            secret_hash=hash_worker_secret(secret),
        )
        session.add(credential)
        await session.commit()
        worker_id, credential_id = registration.id, credential.id
    audit(
        request,
        "worker_provisioned",
        worker_id=str(worker_id),
        credential_id=str(credential_id),
        workspace_id=str(workspace_id),
        actor=str(membership.user_id),
    )
    return WorkerProvisionOut(
        worker_id=worker_id,
        credential_id=credential_id,
        worker_secret=f"{credential_id}.{secret}",
        workspace_id=workspace_id,
    )


@admin_router.get("", response_model=list[WorkerOut])
async def list_workers(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_member()),
    db: AsyncSession = Depends(get_current_session),
) -> list[WorkerOut]:
    result = await db.execute(
        select(WorkerRegistration)
        .where(WorkerRegistration.workspace_id == workspace_id)
        .order_by(WorkerRegistration.registered_at.desc())
    )
    return [_worker_out(w) for w in result.scalars().all()]


async def _get_workspace_worker(
    db: AsyncSession, workspace_id: uuid.UUID, worker_id: uuid.UUID
) -> WorkerRegistration:
    result = await db.execute(
        select(WorkerRegistration).where(
            WorkerRegistration.id == worker_id,
            WorkerRegistration.workspace_id == workspace_id,
        )
    )
    registration = result.scalar_one_or_none()
    if registration is None:
        raise HTTPException(status_code=404, detail="worker not found")
    return registration


@admin_router.get("/{worker_id}", response_model=WorkerOut)
async def get_worker(
    workspace_id: uuid.UUID,
    worker_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_member()),
    db: AsyncSession = Depends(get_current_session),
) -> WorkerOut:
    return _worker_out(await _get_workspace_worker(db, workspace_id, worker_id))


@admin_router.get("/{worker_id}/heartbeats", response_model=list[HeartbeatRecordOut])
async def list_worker_heartbeats(
    workspace_id: uuid.UUID,
    worker_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
    limit: int = 100,
) -> list[HeartbeatRecordOut]:
    """Audit endpoint (design amendment 2): heartbeat telemetry for
    workspace ADMINS. The RLS policy on worker_heartbeats enforces the
    same admin-only rule at the data layer, so even a guard bug here
    could not leak telemetry to normal members.
    """
    await _get_workspace_worker(db, workspace_id, worker_id)
    result = await db.execute(
        select(WorkerHeartbeat)
        .where(WorkerHeartbeat.worker_id == worker_id)
        .order_by(WorkerHeartbeat.heartbeat_at.desc())
        .limit(min(max(limit, 1), 1000))
    )
    return [HeartbeatRecordOut.model_validate(h) for h in result.scalars().all()]


@admin_router.post("/{worker_id}/drain", response_model=WorkerOut)
async def set_worker_drain(
    workspace_id: uuid.UUID,
    worker_id: uuid.UUID,
    payload: WorkerDrainIn,
    request: Request,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> WorkerOut:
    await _get_workspace_worker(db, workspace_id, worker_id)  # 404 + RLS check first
    async with AsyncSessionLocal() as session:
        registration = await session.get(WorkerRegistration, worker_id, with_for_update=True)
        registration.drain = payload.drain
        await session.commit()
        await session.refresh(registration)
        out = _worker_out(registration)
    audit(
        request,
        "worker_drain_set",
        worker_id=str(worker_id),
        drain=payload.drain,
        actor=str(membership.user_id),
    )
    return out


@admin_router.post("/{worker_id}/credentials/rotate", response_model=CredentialRotateOut)
async def rotate_worker_credential(
    workspace_id: uuid.UUID,
    worker_id: uuid.UUID,
    request: Request,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> CredentialRotateOut:
    """Zero-downtime rotation: issues a new ACTIVE credential and gives
    every previously-active credential a grace `expires_at` instead of
    revoking it instantly, so a running worker keeps authenticating until
    it picks up the new secret.
    """
    await _get_workspace_worker(db, workspace_id, worker_id)
    secret = generate_worker_secret()
    now = datetime.now(UTC)
    grace_until = now + timedelta(seconds=settings.worker_credential_rotation_grace_seconds)
    async with AsyncSessionLocal() as session:
        # Serialize against a concurrent revoke (kill switch) on the SAME
        # worker: both take the worker row lock first, so their credential
        # mutations can never interleave. Without this, revoke could SELECT
        # the active set before rotate inserts the new credential and then
        # leave that new credential ACTIVE after the admin "killed" all.
        await session.get(WorkerRegistration, worker_id, with_for_update=True)
        result = await session.execute(
            select(WorkerCredential).where(
                WorkerCredential.worker_id == worker_id,
                WorkerCredential.status == WorkerCredentialStatus.ACTIVE,
            )
        )
        for old in result.scalars().all():
            old.rotated_at = now
            if old.expires_at is None or old.expires_at > grace_until:
                old.expires_at = grace_until
        credential = WorkerCredential(
            worker_id=worker_id,
            workspace_id=workspace_id,
            secret_hash=hash_worker_secret(secret),
        )
        session.add(credential)
        await session.commit()
        credential_id = credential.id
    audit(
        request,
        "worker_credential_rotated",
        worker_id=str(worker_id),
        new_credential_id=str(credential_id),
        actor=str(membership.user_id),
    )
    return CredentialRotateOut(
        credential_id=credential_id,
        worker_secret=f"{credential_id}.{secret}",
        previous_expires_at=grace_until,
    )


@admin_router.post("/{worker_id}/credentials/revoke")
async def revoke_worker_credentials(
    workspace_id: uuid.UUID,
    worker_id: uuid.UUID,
    request: Request,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> dict:
    """Immediate revocation of ALL credentials for a worker (kill switch —
    no grace, unlike rotation)."""
    await _get_workspace_worker(db, workspace_id, worker_id)
    async with AsyncSessionLocal() as session:
        # Lock the worker row first so a concurrent rotate cannot insert a
        # fresh ACTIVE credential between our SELECT and UPDATE — the kill
        # switch must revoke everything active at the instant it runs.
        await session.get(WorkerRegistration, worker_id, with_for_update=True)
        result = await session.execute(
            select(WorkerCredential).where(
                WorkerCredential.worker_id == worker_id,
                WorkerCredential.status == WorkerCredentialStatus.ACTIVE,
            )
        )
        revoked = 0
        for credential in result.scalars().all():
            credential.status = WorkerCredentialStatus.REVOKED
            revoked += 1
        await session.commit()
    audit(
        request,
        "worker_credentials_revoked",
        worker_id=str(worker_id),
        revoked_count=revoked,
        actor=str(membership.user_id),
    )
    return {"revoked": revoked}
