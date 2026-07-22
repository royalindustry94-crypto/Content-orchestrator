"""Transactional outbox producer.

`emit()` is the ONLY way any component writes an event. It never opens
its own transaction — it uses the caller's active session, so the INSERT
lands in the same transaction as whatever domain change the caller just
made. Commit is the caller's responsibility, which is what makes the
domain-change-and-event pair atomic (design doc §3.9, producer txn).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import OutboxEvent
from app.orchestration.events.envelope import EventEnvelope


async def _next_sequence(session: AsyncSession, aggregate_type: str,
    aggregate_id: uuid.UUID) -> int:
    """Per-aggregate monotonic sequence (design doc §3.4). An advisory
    transaction lock scoped to (aggregate_type, aggregate_id) serializes
    concurrent emitters for the same aggregate without locking unrelated
    rows or requiring a separate counter table; it's released automatically
    at COMMIT/ROLLBACK, so it never outlives the caller's transaction.
    """
    await session.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": f"{aggregate_type}:{aggregate_id}"},
    )
    result = await session.execute(
        text(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM outbox_events "
            "WHERE aggregate_type = :t AND aggregate_id = :a"
        ),
        {"t": aggregate_type, "a": str(aggregate_id)},
    )
    return result.scalar_one()


async def emit(
    session: AsyncSession,
    *,
    event_type: str,
    workspace_id: uuid.UUID,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    correlation_id: uuid.UUID,
    payload: dict,
    produced_by: str,
    causation_id: uuid.UUID | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    event_version: int = 1,
) -> OutboxEvent:
    """Insert one outbox event into the CALLER's transaction. Does not
    commit. Returns the ORM object (event_id is already populated) so the
    caller can use it as a causation_id for further events in the same
    unit of work.
    """
    sequence = await _next_sequence(session, aggregate_type, aggregate_id)
    event = OutboxEvent(
        event_id=uuid.uuid4(),
        workspace_id=workspace_id,
        event_type=event_type,
        event_version=event_version,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        correlation_id=correlation_id,
        causation_id=causation_id,
        trace_id=trace_id,
        span_id=span_id,
        sequence=sequence,
        payload=payload,
        occurred_at=datetime.now(timezone.utc),
        produced_by=produced_by,
    )
    session.add(event)
    await session.flush()  # assigns defaults, surfaces constraint errors early — still no commit
    return event


async def emit_envelope(session: AsyncSession, envelope: EventEnvelope) -> OutboxEvent:
    """Same as emit(), taking a pre-built EventEnvelope (useful when a
    caller constructs the envelope up front, e.g. to log it before commit).
    """
    return await emit(
        session,
        event_type=envelope.event_type,
        workspace_id=envelope.workspace_id,
        aggregate_type=envelope.aggregate_type,
        aggregate_id=envelope.aggregate_id,
        correlation_id=envelope.correlation_id,
        payload=envelope.payload,
        produced_by=envelope.produced_by,
        causation_id=envelope.causation_id,
        trace_id=envelope.trace_id,
        span_id=envelope.span_id,
        event_version=envelope.event_version,
    )
