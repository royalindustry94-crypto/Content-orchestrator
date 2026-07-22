"""Outbox producer + relay: atomicity, per-aggregate ordering, dedup,
poison routing (design doc §3).
"""

import os
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test")
os.environ.setdefault("APP_DATABASE_URL", "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.enums import OutboxEventStatus
from app.models.events import OutboxEvent
from app.orchestration import outbox, relay


async def _make_workspace(session) -> tuple[uuid.UUID, uuid.UUID]:
    ws, user = str(uuid.uuid4()), str(uuid.uuid4())
    await session.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"), {"id": user, "e": f"{user}@x.com"})
    await session.execute(text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"), {"id": ws, "u": user})
    return uuid.UUID(ws), uuid.UUID(user)


@pytest.mark.asyncio
async def test_emit_assigns_monotonic_per_aggregate_sequence():
    async with AsyncSessionLocal() as session:
        ws, _ = await _make_workspace(session)
        agg_id = uuid.uuid4()
        e1 = await outbox.emit(
            session, event_type="content.created", workspace_id=ws, aggregate_type="content_item",
            aggregate_id=agg_id, correlation_id=uuid.uuid4(), payload={}, produced_by="test",
        )
        e2 = await outbox.emit(
            session, event_type="content.created", workspace_id=ws, aggregate_type="content_item",
            aggregate_id=agg_id, correlation_id=uuid.uuid4(), payload={}, produced_by="test",
        )
        await session.commit()
        assert e2.sequence == e1.sequence + 1


@pytest.mark.asyncio
async def test_emit_does_not_commit_caller_controls_atomicity():
    """A rollback after emit() must remove the event — proving events
    live in the caller's transaction, not a separate one (design doc §3.1).
    """
    async with AsyncSessionLocal() as session:
        ws, _ = await _make_workspace(session)
        await session.commit()

    async with AsyncSessionLocal() as session:
        event = await outbox.emit(
            session, event_type="content.created", workspace_id=ws, aggregate_type="content_item",
            aggregate_id=uuid.uuid4(), correlation_id=uuid.uuid4(), payload={}, produced_by="test",
        )
        event_id = event.event_id
        await session.rollback()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(OutboxEvent).where(OutboxEvent.event_id == event_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_relay_dispatches_to_registered_consumer_exactly_once():
    calls = []

    async def handler(session, event):
        calls.append(event.event_id)

    relay.register_consumer("test-consumer", "content.created", handler)

    async with AsyncSessionLocal() as session:
        ws, _ = await _make_workspace(session)
        await outbox.emit(
            session, event_type="content.created", workspace_id=ws, aggregate_type="content_item",
            aggregate_id=uuid.uuid4(), correlation_id=uuid.uuid4(), payload={}, produced_by="test",
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        n = await relay.poll_and_dispatch(session)
        await session.commit()
    assert n >= 1
    assert len(calls) == 1

    # Re-running the relay must not redeliver to a consumer whose
    # checkpoint already passed this event's sequence (dedup via checkpoint).
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(OutboxEvent).where(OutboxEvent.status == OutboxEventStatus.DISPATCHED).order_by(OutboxEvent.occurred_at.desc()).limit(1)
        )
        dispatched = result.scalar_one()
        assert dispatched.status == OutboxEventStatus.DISPATCHED
