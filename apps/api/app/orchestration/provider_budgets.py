"""Provider concurrency budgets (WS4).

When a workspace configures a budget for a provider, claim/dispatch may
not put more than ``max_concurrent`` DISPATCHED/ACKNOWLEDGED assignments
with that provider in flight. Missing budget ⇒ no limit (fail-open).
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.assignments import StageAssignment
from app.models.backpressure import ProviderConcurrencyBudget
from app.models.enums import StageAssignmentStatus


async def lock_budget(
    session: AsyncSession, *, workspace_id: uuid.UUID, provider: str
) -> ProviderConcurrencyBudget | None:
    result = await session.execute(
        select(ProviderConcurrencyBudget)
        .where(
            ProviderConcurrencyBudget.workspace_id == workspace_id,
            ProviderConcurrencyBudget.provider == provider,
        )
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def count_inflight(
    session: AsyncSession, *, workspace_id: uuid.UUID, provider: str
) -> int:
    result = await session.execute(
        select(func.count(StageAssignment.id)).where(
            StageAssignment.workspace_id == workspace_id,
            StageAssignment.provider == provider,
            StageAssignment.status.in_(
                [StageAssignmentStatus.DISPATCHED, StageAssignmentStatus.ACKNOWLEDGED]
            ),
        )
    )
    return int(result.scalar_one() or 0)


async def has_provider_capacity(
    session: AsyncSession, *, workspace_id: uuid.UUID, provider: str | None
) -> bool:
    """Return True if ``provider`` is None/blank or under budget."""
    if not provider:
        return True
    budget = await lock_budget(session, workspace_id=workspace_id, provider=provider)
    if budget is None:
        return True
    inflight = await count_inflight(session, workspace_id=workspace_id, provider=provider)
    return inflight < budget.max_concurrent
