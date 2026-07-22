"""Outbox relay: polls outbox_events and delivers to in-process consumer
handlers, tracking per-consumer checkpoints so redelivery is safe and
replay is possible (design doc §3.1, §3.5, §3.6, §3.8).

This milestone's consumers are in-process Python callables. A future
broker adapter would implement the same delivery contract (checkpoint,
dedup, poison routing) against an external system without changing
producers — the point of the transactional-outbox + relay split.
"""

from __future__ import annotations

import logging
import uuid
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import OutboxEventStatus
from app.models.events import ConsumerCheckpoint, EventConsumer, OutboxEvent
from app.orchestration.retry import route_to_dead_letter

logger = logging.getLogger(__name__)

Handler = Callable[[AsyncSession, OutboxEvent], Awaitable[None]]

# consumer_name -> (event_type -> handler). Registered by whichever module
# owns that reaction (e.g. the controller registers its own handlers at
# import time via register_consumer below).
_REGISTRY: dict[str, dict[str, Handler]] = {}


def register_consumer(consumer_name: str, event_type: str, handler: Handler) -> None:
    _REGISTRY.setdefault(consumer_name, {})[event_type] = handler


async def _get_or_create_consumer(session: AsyncSession, name: str) -> EventConsumer:
    result = await session.execute(select(EventConsumer).where(EventConsumer.name == name))
    consumer = result.scalar_one_or_none()
    if consumer is None:
        consumer = EventConsumer(id=uuid.uuid4(), name=name)
        session.add(consumer)
        await session.flush()
    return consumer


async def _get_or_create_checkpoint(
    session: AsyncSession, consumer_id: uuid.UUID, aggregate_type: str, partition_key: str
) -> ConsumerCheckpoint:
    result = await session.execute(
        select(ConsumerCheckpoint).where(
            ConsumerCheckpoint.consumer_id == consumer_id,
            ConsumerCheckpoint.aggregate_type == aggregate_type,
            ConsumerCheckpoint.partition_key == partition_key,
        )
    )
    checkpoint = result.scalar_one_or_none()
    if checkpoint is None:
        checkpoint = ConsumerCheckpoint(
            id=uuid.uuid4(), consumer_id=consumer_id,
            aggregate_type=aggregate_type, partition_key=partition_key, last_sequence=0,
        )
        session.add(checkpoint)
        await session.flush()
    return checkpoint


async def dispatch_one(session: AsyncSession, event: OutboxEvent) -> None:
    """Deliver one event to every registered consumer whose checkpoint
    hasn't already passed it. Marks the event dispatched (all consumers
    succeeded or had nothing to do) or leaves it pending for retry, or
    poisons it for a specific consumer once that consumer exhausts
    max_delivery_attempts (other consumers are unaffected — no
    head-of-line blocking across consumers, per design doc §3.8).
    """
    any_pending = False
    for consumer_name, handlers in _REGISTRY.items():
        handler = handlers.get(event.event_type)
        if handler is None:
            continue
        consumer = await _get_or_create_consumer(session, consumer_name)
        checkpoint = await _get_or_create_checkpoint(
            session, consumer.id, event.aggregate_type, str(event.aggregate_id)
        )
        if checkpoint.last_sequence >= event.sequence:
            continue  # already applied by this consumer — dedup
        try:
            await handler(session, event)
            checkpoint.last_sequence = event.sequence
        except Exception as exc:  # noqa: BLE001 — must not crash the relay loop
            event.delivery_attempts += 1
            logger.warning(
                "consumer handler failed",
                extra={
                    "event_id": str(event.event_id), "event_type": event.event_type,
                    "consumer": consumer_name, "attempt": event.delivery_attempts,
                    "error": str(exc), "correlation_id": str(event.correlation_id),
                    "trace_id": event.trace_id,
                },
            )
            if event.delivery_attempts >= consumer.max_delivery_attempts:
                event.status = OutboxEventStatus.POISON
                await route_to_dead_letter(
                    session,
                    workspace_id=event.workspace_id,
                    related_table="outbox_events",
                    related_id=event.event_id,
                    job_type=f"event_consumer:{consumer_name}",
                    payload=event.payload,
                    failure_reason=str(exc),
                    attempt_count=event.delivery_attempts,
                    first_failed_at=event.occurred_at,
                )
            else:
                any_pending = True

    if event.status != OutboxEventStatus.POISON and not any_pending:
        event.status = OutboxEventStatus.DISPATCHED


async def poll_and_dispatch(session: AsyncSession, *, batch_size: int = 50) -> int:
    """One relay tick. Caller owns the session/transaction and commits
    after this returns. Uses FOR UPDATE SKIP LOCKED so multiple relay
    replicas partition work with zero coordination (design doc §3.1, §4.5
    principle applied to the relay too).
    """
    result = await session.execute(
        select(OutboxEvent)
        .where(OutboxEvent.status == OutboxEventStatus.PENDING)
        .order_by(OutboxEvent.occurred_at)
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )
    events = list(result.scalars().all())
    for event in events:
        await dispatch_one(session, event)
    return len(events)
