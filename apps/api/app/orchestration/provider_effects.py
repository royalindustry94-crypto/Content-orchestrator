"""Provider effect key recording (WS3 duplicate-execution prevention).

Inserts a durable key before a provider-facing side effect. A unique
constraint conflict means this assignment already produced (or is already
producing) its effect — callers treat that as an idempotent no-op rather
than double-firing the provider.

The default key is derived from ``assignment_id`` alone, not
``(assignment_id, attempt_number)`` (2026-09-07 fix — see
`docs/TECHNICAL_DEBT_REGISTER.md` TD-077). A single assignment must
produce at most one committed provider effect across every attempt it
takes: `app.orchestration.recovery` bumps `attempt_number` and re-queues
the *same* assignment on crash/lease-expiry recovery specifically because
"the attempt is the unit that reserves budget ... an attempt that reached
a worker may already have produced a billable, non-idempotent side
effect" — so the dedup key must survive that bump, or a worker that
reliably crashes right after triggering a real provider call would
re-trigger it on every recovered attempt, up to `assignment_default_max_attempts`
times, before the unique-key check ever caught it.
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
    """`attempt_number` is accepted (and still stored on the row, see
    `ensure_provider_effect_key`) for audit/debugging purposes only — it is
    deliberately NOT part of the key, so every attempt of the same
    assignment maps to the same dedup key. See module docstring.
    """
    del attempt_number
    return str(assignment_id)


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
