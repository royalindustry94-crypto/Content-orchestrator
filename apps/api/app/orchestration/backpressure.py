"""Queue-depth back-pressure evaluation (WS4).

Observes PENDING assignment depth per workspace, upserts
``workspace_backpressure_state``, and emits ENTERED/CLEARED outbox events
on real transitions. Never drops work.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.assignments import StageAssignment
from app.models.backpressure import WorkspaceBackpressureState
from app.models.enums import BackpressureState, StageAssignmentStatus
from app.models.scheduling import WorkspaceConcurrencyLimit
from app.orchestration.events.envelope import child_span
from app.orchestration.events.types import BACKPRESSURE_CLEARED, BACKPRESSURE_ENTERED
from app.orchestration.outbox import emit


@dataclass(frozen=True)
class BackpressureSnapshot:
    workspace_id: uuid.UUID
    state: BackpressureState
    pending_depth: int
    soft_limit: int
    hard_limit: int
    changed: bool


def classify_depth(depth: int, *, soft: int, hard: int) -> BackpressureState:
    if depth >= hard:
        return BackpressureState.THROTTLED
    if depth >= soft:
        return BackpressureState.PRESSURED
    return BackpressureState.NORMAL


async def pending_depth(session: AsyncSession, workspace_id: uuid.UUID) -> int:
    result = await session.execute(
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.status == StageAssignmentStatus.PENDING,
        )
    )
    return int(result.scalar_one() or 0)


async def _limits(session: AsyncSession, workspace_id: uuid.UUID) -> tuple[int, int, int]:
    """Return (soft, hard, max_per_tick)."""
    settings = get_settings()
    result = await session.execute(
        select(WorkspaceConcurrencyLimit).where(
            WorkspaceConcurrencyLimit.workspace_id == workspace_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return (
            settings.queue_soft_limit_default,
            settings.queue_hard_limit_default,
            5,
        )
    return row.queue_soft_limit, row.queue_hard_limit, row.max_per_scheduler_tick


async def evaluate_workspace_backpressure(
    session: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    now: datetime | None = None,
    correlation_id: uuid.UUID | None = None,
) -> BackpressureSnapshot:
    now = now or datetime.now(UTC)
    soft, hard, _ = await _limits(session, workspace_id)
    depth = await pending_depth(session, workspace_id)
    new_state = classify_depth(depth, soft=soft, hard=hard)

    result = await session.execute(
        select(WorkspaceBackpressureState)
        .where(WorkspaceBackpressureState.workspace_id == workspace_id)
        .with_for_update()
    )
    row = result.scalar_one_or_none()
    previous = row.state if row is not None else BackpressureState.NORMAL
    changed = previous != new_state

    if row is None:
        row = WorkspaceBackpressureState(
            workspace_id=workspace_id,
            state=new_state,
            pending_depth=depth,
            entered_at=now if new_state != BackpressureState.NORMAL else None,
            updated_at=now,
        )
        session.add(row)
    else:
        row.state = new_state
        row.pending_depth = depth
        row.updated_at = now
        if changed:
            row.entered_at = now if new_state != BackpressureState.NORMAL else None

    if changed:
        trace_id, span_id = child_span(None)
        event_type = (
            BACKPRESSURE_CLEARED if new_state == BackpressureState.NORMAL else BACKPRESSURE_ENTERED
        )
        await emit(
            session,
            event_type=event_type,
            workspace_id=workspace_id,
            aggregate_type="workspace",
            aggregate_id=workspace_id,
            correlation_id=correlation_id or uuid.uuid4(),
            trace_id=trace_id,
            span_id=span_id,
            payload={
                "state": new_state.value,
                "previous_state": previous.value,
                "pending_depth": depth,
                "soft_limit": soft,
                "hard_limit": hard,
            },
            produced_by="backpressure",
        )

    return BackpressureSnapshot(
        workspace_id=workspace_id,
        state=new_state,
        pending_depth=depth,
        soft_limit=soft,
        hard_limit=hard,
        changed=changed,
    )


async def evaluate_all_active_workspaces(
    session: AsyncSession, *, batch_size: int = 100
) -> list[BackpressureSnapshot]:
    """Evaluate workspaces that currently have PENDING assignments."""
    result = await session.execute(
        select(StageAssignment.workspace_id)
        .where(StageAssignment.status == StageAssignmentStatus.PENDING)
        .group_by(StageAssignment.workspace_id)
        .limit(batch_size)
    )
    snapshots: list[BackpressureSnapshot] = []
    for (workspace_id,) in result.all():
        snapshots.append(await evaluate_workspace_backpressure(session, workspace_id))
    return snapshots


async def effective_scheduler_tick_limit(
    session: AsyncSession, workspace_id: uuid.UUID, configured: int
) -> int:
    """Halve tick allowance when THROTTLED (min 1). Never zero."""
    result = await session.execute(
        select(WorkspaceBackpressureState.state).where(
            WorkspaceBackpressureState.workspace_id == workspace_id
        )
    )
    state = result.scalar_one_or_none()
    if state == BackpressureState.THROTTLED:
        return max(1, configured // 2)
    return configured
