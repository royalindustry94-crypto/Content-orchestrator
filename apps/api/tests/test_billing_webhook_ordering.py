"""H-5 closure: repository-side Stripe webhook duplicate / replay / ordering.

Live Stripe signature delivery stays external (BLOCKED — EXTERNAL EVIDENCE
REQUIRED); everything reachable without live credentials is asserted here
against real PostgreSQL, including that business state is never mutated
before the duplicate-event guard has claimed the event id.
"""

from __future__ import annotations

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
) -> dict:
    end = period_end or (datetime.now(UTC) + timedelta(days=30))
    return {
        "id": event_id,
        "type": event_type,
        "created": int(end.timestamp()),
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
