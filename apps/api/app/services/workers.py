"""Worker liveness: server-driven offline detection and computed liveness.

All liveness decisions use the API/database server clock exclusively.
Worker-reported timestamps are never trusted (heartbeat times are
assigned server-side), so worker clock skew cannot affect liveness —
the documented skew assumption is therefore "irrelevant by construction"
for liveness, and only matters for credential expiry, which also uses the
server clock (see app.core.worker_auth).

WS3: ``mark_stale_workers_offline`` returns the flipped worker ids so the
maintenance tick can reap their in-flight assignments in the same
transaction (closing the load=0 / still-DISPATCHED window).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkerStatus
from app.models.workers import WorkerRegistration

LIVENESS_HEALTHY = "healthy"
LIVENESS_SUSPECT = "suspect"
LIVENESS_DEAD = "dead"


def compute_liveness(
    last_heartbeat_at: datetime | None,
    *,
    now: datetime | None = None,
    suspect_after_seconds: int,
    offline_after_seconds: int,
) -> str:
    if last_heartbeat_at is None:
        return LIVENESS_DEAD
    now = now or datetime.now(UTC)
    age = (now - last_heartbeat_at).total_seconds()
    if age < suspect_after_seconds:
        return LIVENESS_HEALTHY
    if age < offline_after_seconds:
        return LIVENESS_SUSPECT
    return LIVENESS_DEAD


async def select_stale_worker_ids(
    session: AsyncSession,
    *,
    offline_after_seconds: int,
    now: datetime | None = None,
) -> list[uuid.UUID]:
    """Return ids of workers that would be flipped offline (locked)."""
    now = now or datetime.now(UTC)
    result = await session.execute(
        select(WorkerRegistration.id)
        .where(
            WorkerRegistration.deregistered_at.is_(None),
            WorkerRegistration.status != WorkerStatus.OFFLINE,
            (
                WorkerRegistration.last_heartbeat_at.is_(None)
                | (
                    WorkerRegistration.last_heartbeat_at
                    < now - timedelta(seconds=offline_after_seconds)
                )
            ),
        )
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


async def mark_stale_workers_offline(
    session: AsyncSession,
    *,
    offline_after_seconds: int,
    now: datetime | None = None,
) -> list[uuid.UUID]:
    """Server-driven offline detection: flip workers whose last heartbeat
    is older than the threshold to OFFLINE and zero their load. Returns
    the flipped worker ids (empty when nothing changed).

    `now` is injectable for clock-controlled tests only; production
    callers use the real server clock.
    """
    now = now or datetime.now(UTC)
    stale_ids = await select_stale_worker_ids(
        session, offline_after_seconds=offline_after_seconds, now=now
    )
    if not stale_ids:
        return []
    await session.execute(
        update(WorkerRegistration)
        .where(WorkerRegistration.id.in_(stale_ids))
        .values(status=WorkerStatus.OFFLINE, current_load=0)
    )
    return stale_ids
