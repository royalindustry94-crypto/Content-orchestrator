"""H-5 closure: repository-side Stripe webhook duplicate / replay / ordering.

Live Stripe signature delivery stays external (BLOCKED — EXTERNAL EVIDENCE
REQUIRED); everything reachable without live credentials is asserted here
against real PostgreSQL, including that business state is never mutated
before the duplicate-event guard has claimed the event id.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.billing import BillingWebhookEvent, WorkspaceBilling
from app.services import billing as billing_service


@pytest.fixture
def billing_on(monkeypatch):
    monkeypatch.setenv("BILLING_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_ordering")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_ordering")
    monkeypatch.setenv("STRIPE_PRICE_ID_PRO", "price_pro_ordering")
    monkeypatch.setenv("STRIPE_CHECKOUT_SUCCESS_URL", "http://localhost:5173/ok")
    monkeypatch.setenv("STRIPE_CHECKOUT_CANCEL_URL", "http://localhost:5173/no")
    get_settings.cache_clear()
    yield
    for key in (
        "BILLING_ENABLED",
        "STRIPE_SECRET_KEY",
        "STRIPE_WEBHOOK_SECRET",
        "STRIPE_PRICE_ID_PRO",
        "STRIPE_CHECKOUT_SUCCESS_URL",
        "STRIPE_CHECKOUT_CANCEL_URL",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()


async def _workspace(session) -> uuid.UUID:
    ws, user = str(uuid.uuid4()), str(uuid.uuid4())
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
        {"id": user, "e": f"{user}@x.com"},
    )
    await session.execute(
        text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'bill', :u)"),
        {"id": ws, "u": user},
    )
    await session.commit()
    return uuid.UUID(ws)


def _subscription_event(
    *, event_id: str, workspace_id: uuid.UUID, status: str, sub_id: str,
    event_type: str = "customer.subscription.updated", period_end: datetime | None = None,
    created: int | None = None,
) -> dict:
    end = period_end or (datetime.now(UTC) + timedelta(days=30))
    return {
        "id": event_id,
        "type": event_type,
        "created": created if created is not None else int(end.timestamp()),
        "data": {
            "object": {
                "id": sub_id,
                "object": "subscription",
                "status": status,
                "customer": f"cus_{sub_id}",
                "current_period_end": int(end.timestamp()),
                "cancel_at_period_end": False,
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }


async def _receipts(session, event_id: str) -> int:
    return (
        await session.execute(
            select(func.count(BillingWebhookEvent.id)).where(
                BillingWebhookEvent.stripe_event_id == event_id
            )
        )
    ).scalar_one()


@pytest.mark.asyncio
async def test_duplicate_and_replayed_event_is_idempotent(billing_on):
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        event = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub,
        )

        first = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
        assert first["status"] == "processed"

        # Exact replay of the same event id (Stripe retry).
        second = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
        assert second["status"] == "duplicate"

        # A replay carrying a *different* payload for the same id must not be
        # applied either — the event id is the idempotency boundary.
        tampered = dict(event)
        tampered["data"] = {
            "object": {
                **event["data"]["object"],
                "status": "canceled",
            }
        }
        third = await billing_service.process_stripe_event(session, event=tampered)
        await session.commit()
        assert third["status"] == "duplicate"

        assert await _receipts(session, event["id"]) == 1
        row = await session.get(WorkspaceBilling, ws)
        assert row is not None
        assert row.status == "active"
        assert row.plan == "pro"
        assert billing_service.is_entitled(row, billing_enabled=True) is True


@pytest.mark.asyncio
async def test_out_of_order_events_converge_on_latest_delivered_state(billing_on):
    """Stripe does not guarantee ordering. Each distinct event is applied
    once; a later-delivered cancellation must end the entitlement, and a
    re-delivery of the older 'active' event must not resurrect it.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        created = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub, event_type="customer.subscription.created",
        )
        deleted = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="canceled", sub_id=sub, event_type="customer.subscription.deleted",
        )

        await billing_service.process_stripe_event(session, event=created)
        await session.commit()
        await billing_service.process_stripe_event(session, event=deleted)
        await session.commit()

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None and row.status == "canceled"
        assert billing_service.is_entitled(row, billing_enabled=True) is False

        # Re-delivery of the older event must be rejected as duplicate and
        # must not flip the workspace back to entitled.
        again = await billing_service.process_stripe_event(session, event=created)
        await session.commit()
        assert again["status"] == "duplicate"
        await session.refresh(row)
        assert row.status == "canceled"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_delayed_older_event_does_not_resurrect_a_newer_cancellation(billing_on):
    """Two *distinct* events (different ids) for the same subscription: an
    older 'active' update and a newer cancellation. Stripe explicitly does
    not guarantee delivery order, so the older event can arrive at this
    service *after* the newer one has already been applied. It must not
    overwrite the newer state — this is different from literal event-id
    redelivery, which the duplicate-receipt guard already handles.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        base = int(datetime.now(UTC).timestamp())
        older_active = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub, event_type="customer.subscription.updated",
            created=base,
        )
        newer_canceled = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="canceled", sub_id=sub, event_type="customer.subscription.deleted",
            created=base + 3600,
        )

        # Newer event arrives and is applied first (realistic: the older
        # event's original delivery attempt failed and Stripe is retrying it).
        first = await billing_service.process_stripe_event(session, event=newer_canceled)
        await session.commit()
        assert first["status"] == "processed"

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None and row.status == "canceled"
        assert billing_service.is_entitled(row, billing_enabled=True) is False

        # The older event now arrives late, as a genuinely distinct event
        # (not a redelivery) — it must be accepted as a receipt (not a
        # duplicate) but must NOT resurrect entitlement.
        second = await billing_service.process_stripe_event(session, event=older_active)
        await session.commit()
        assert second["status"] == "processed"

        await session.refresh(row)
        assert row.status == "canceled"
        assert row.plan == "none"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_failed_handler_rolls_back_receipt_and_state(billing_on):
    """A handler error must leave no receipt and no partial mutation, so
    Stripe's retry is processed cleanly rather than being swallowed as a
    duplicate of a half-applied event.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        unmappable = {
            "id": event_id,
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": f"sub_{uuid.uuid4().hex[:10]}",
                    "status": "active",
                    "customer": f"cus_{uuid.uuid4().hex[:10]}",
                    "metadata": {},
                }
            },
        }

        with pytest.raises(billing_service.BillingError) as err:
            await billing_service.process_stripe_event(session, event=unmappable)
        assert err.value.code == "unknown_subscription"
        await session.rollback()

        assert await _receipts(session, event_id) == 0, (
            "a failed handler must not leave an event receipt behind"
        )

        # The retry, now mappable, is processed exactly once.
        retry = _subscription_event(
            event_id=event_id, workspace_id=ws, status="active",
            sub_id=f"sub_{uuid.uuid4().hex[:10]}",
        )
        result = await billing_service.process_stripe_event(session, event=retry)
        await session.commit()
        assert result["status"] == "processed"
        assert await _receipts(session, event_id) == 1


@pytest.mark.asyncio
async def test_checkout_completion_alone_never_grants_entitlement(billing_on):
    """Linkage only: checkout.session.completed records customer/subscription
    ids but must not make the workspace entitled without a subscription
    lifecycle event.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        checkout = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": f"cs_{uuid.uuid4().hex[:10]}",
                    "customer": f"cus_{sub}",
                    "subscription": sub,
                    "payment_status": "paid",
                    "client_reference_id": str(ws),
                    "metadata": {"workspace_id": str(ws)},
                }
            },
        }
        result = await billing_service.process_stripe_event(session, event=checkout)
        await session.commit()
        assert result["status"] == "processed"

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None
        assert row.stripe_subscription_id == sub
        assert row.plan == "none"
        assert row.status == "inactive"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_payment_failure_revokes_entitlement_without_losing_plan_marker(billing_on):
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        await billing_service.process_stripe_event(
            session,
            event=_subscription_event(
                event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
                status="active", sub_id=sub,
            ),
        )
        await session.commit()

        failed = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "invoice.payment_failed",
            "data": {"object": {"id": f"in_{uuid.uuid4().hex[:10]}", "subscription": sub}},
        }
        result = await billing_service.process_stripe_event(session, event=failed)
        await session.commit()
        assert result["status"] == "processed"

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None
        assert row.status == "past_due"
        assert row.plan == "pro", "plan marker is retained for operator visibility"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_ensure_workspace_billing_for_update_locks_concurrent_readers(billing_on):
    """MEDIUM-2: Stripe does not guarantee single-threaded webhook delivery.
    ``ensure_workspace_billing(..., for_update=True)`` — used by
    ``_apply_subscription`` — must take a real row lock, so a second,
    genuinely concurrent transaction touching the same workspace's billing
    row blocks until the first commits instead of racing it on an unlocked
    read-modify-write.
    """
    async with AsyncSessionLocal() as setup:
        ws = await _workspace(setup)
        # Seed the row so both sides hit the SELECT ... FOR UPDATE path
        # rather than the INSERT path.
        await billing_service.ensure_workspace_billing(setup, workspace_id=ws)
        await setup.commit()

    holder = AsyncSessionLocal()
    waiter = AsyncSessionLocal()
    try:
        locked = await billing_service.ensure_workspace_billing(
            holder, workspace_id=ws, for_update=True
        )
        locked.status = "active"
        locked.plan = "pro"
        await holder.flush()  # applies the write; lock is only released on commit/rollback

        waiter_task = asyncio.create_task(
            billing_service.ensure_workspace_billing(waiter, workspace_id=ws, for_update=True)
        )
        await asyncio.sleep(0.2)
        assert not waiter_task.done(), (
            "a concurrent for_update=True read must block on the held row "
            "lock, not proceed past it"
        )

        await holder.commit()
        waiter_row = await asyncio.wait_for(waiter_task, timeout=5)
        assert waiter_row.status == "active"
        await waiter.commit()
    finally:
        await holder.close()
        await waiter.close()
