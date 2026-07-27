"""Provider effect key recording (WS3 duplicate-execution prevention).

Inserts a durable key before a provider-facing side effect. A unique
constraint conflict means this attempt already executed — callers treat
that as an idempotent no-op rather than double-firing the provider.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.provider_effects import ProviderEffectKey


@dataclass(frozen=True)
class EffectKeyResult:
    effect_key: str
    created: bool  # False => duplicate; side effect must not re-run


def default_effect_key(assignment_id: uuid.UUID, attempt_number: int) -> str:
    return f"{assignment_id}:{attempt_number}"


async def ensure_provider_effect_key(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    assignment_id: uuid.UUID,
    attempt_number: int,
    effect_kind: str = "stage_execute",
    effect_key: str | None = None,
) -> EffectKeyResult:
    """Record the effect key. Returns ``created=False`` on unique conflict
    (after rolling back only the failed INSERT via savepoint).
    """
    key = effect_key or default_effect_key(assignment_id, attempt_number)
    try:
        async with session.begin_nested():
            session.add(
                ProviderEffectKey(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    assignment_id=assignment_id,
                    attempt_number=attempt_number,
                    effect_key=key,
                    effect_kind=effect_kind,
                )
            )
            await session.flush()
        return EffectKeyResult(effect_key=key, created=True)
    except IntegrityError:
        return EffectKeyResult(effect_key=key, created=False)
