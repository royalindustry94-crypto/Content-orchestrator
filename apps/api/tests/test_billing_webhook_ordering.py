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
async def test_equal_timestamp_active_event_does_not_win_over_a_cancellation(billing_on):
    """Stripe `created` is second-granularity, so two distinct events for the
    same subscription can share the exact same timestamp. A tie must not let
    whichever event is merely delivered/processed *last* decide the outcome:
    an entitlement-granting event tied with an already-applied cancellation
    must lose, while the cancellation itself is always safe to apply.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        tie = int(datetime.now(UTC).timestamp())
        canceled = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="canceled", sub_id=sub, event_type="customer.subscription.deleted",
            created=tie,
        )
        active_same_instant = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub, event_type="customer.subscription.updated",
            created=tie,
        )

        first = await billing_service.process_stripe_event(session, event=canceled)
        await session.commit()
        assert first["status"] == "processed"

        second = await billing_service.process_stripe_event(session, event=active_same_instant)
        await session.commit()
        assert second["status"] == "processed"

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None
        assert row.status == "canceled"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_delayed_older_subscription_downgrade_does_not_overwrite_a_newer_active_state(
    billing_on,
):
    """Codex P1 on b58adb7: _apply_subscription's staleness guard only
    rejected a stale/tied event when it was entitlement-*granting*
    (``stale_or_tied and is_entitling``) — a stale/tied *downgrade*
    (past_due/unpaid/incomplete via customer.subscription.updated) always
    applied unconditionally, on the theory that moving out of entitlement is
    always safe. That's true for a genuine terminal cancellation
    (subscription.deleted is authoritative regardless of delivery order —
    once really canceled, nothing legitimately supersedes it for that
    subscription id), but a `past_due`/`unpaid`/`incomplete` status is a
    *reversible* sub-state of an ongoing subscription, not terminal — a
    strictly older one arriving late must not overwrite a newer, already-
    applied `active` state, exactly the same delayed-retry hazard already
    fixed for invoice.payment_failed's own branch. Unambiguous staleness
    (strictly older, not just tied) must be rejected regardless of
    direction; only a genuine timestamp *tie* keeps the fail-closed
    exception that favors a downgrade.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        base = int(datetime.now(UTC).timestamp())

        await billing_service.process_stripe_event(
            session,
            event=_subscription_event(
                event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
                status="active", sub_id=sub, created=base + 3600,
            ),
        )
        await session.commit()

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None and row.status == "active"

        # A stale, distinct customer.subscription.updated "past_due" event —
        # strictly older than the applied "active" event, e.g. a delayed
        # retry of an earlier failed-payment update that has since been
        # resolved — arrives late.
        stale_past_due = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="past_due", sub_id=sub, created=base,
        )
        result = await billing_service.process_stripe_event(session, event=stale_past_due)
        await session.commit()
        assert result["status"] == "processed"

        await session.refresh(row)
        assert row.status == "active", (
            "a strictly-older subscription downgrade must not overwrite a "
            "newer already-applied active state"
        )
        assert billing_service.is_entitled(row, billing_enabled=True) is True


@pytest.mark.asyncio
async def test_delayed_older_active_event_does_not_resurrect_a_payment_failure(billing_on):
    """invoice.payment_failed sets status="past_due" directly, bypassing
    _apply_subscription's ordering check entirely. If a *distinct*, older
    customer.subscription.updated "active" event (Stripe's own retry of an
    earlier delivery attempt) arrives afterward, it must not overwrite the
    payment failure — the payment failure is the newer, authoritative state
    even though it was applied through a different code path.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        base = int(datetime.now(UTC).timestamp())

        await billing_service.process_stripe_event(
            session,
            event=_subscription_event(
                event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
                status="active", sub_id=sub, created=base,
            ),
        )
        await session.commit()

        failed = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "invoice.payment_failed",
            "created": base + 3600,
            "data": {"object": {"id": f"in_{uuid.uuid4().hex[:10]}", "subscription": sub}},
        }
        first = await billing_service.process_stripe_event(session, event=failed)
        await session.commit()
        assert first["status"] == "processed"

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None and row.status == "past_due"

        # A stale, distinct "active" event — older than the payment failure —
        # arrives late. It must be recorded as a receipt but must not
        # resurrect entitlement.
        stale_active = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub, created=base + 1800,
        )
        second = await billing_service.process_stripe_event(session, event=stale_active)
        await session.commit()
        assert second["status"] == "processed"

        await session.refresh(row)
        assert row.status == "past_due"
        assert billing_service.is_entitled(row, billing_enabled=True) is False


@pytest.mark.asyncio
async def test_delayed_older_payment_failure_does_not_revoke_a_newer_active_state(billing_on):
    """Mirror image of test_delayed_older_active_event_does_not_resurrect_a_
    payment_failure: invoice.payment_failed's own handler set status =
    "past_due" completely unconditionally, with no ordering check at all
    (widening _latest_applied_event_created's read-side filter only helps
    other events that check it — it does not make this handler check
    anything). So a stale, delayed invoice.payment_failed retry — older
    than a customer.subscription.updated "active" event that has already
    been applied (e.g. the customer fixed their card and renewed) — could
    incorrectly revoke entitlement from an already-current, paying
    workspace, since Stripe retries webhook delivery for days and a
    payment-failure notification isn't authoritative about *current*
    subscription state the way a terminal status transition is. Unlike a
    subscription cancellation (always safe to apply immediately — a real
    cancellation is inherently the terminal truth), a payment-failure event
    only describes a single invoice attempt at a point in time and can be
    superseded by a later successful renewal, so it must lose an ordering
    comparison against a newer already-applied event.
    """
    async with AsyncSessionLocal() as session:
        ws = await _workspace(session)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        base = int(datetime.now(UTC).timestamp())

        # Newer "active" event applied first (realistic: the customer's
        # renewal succeeded and Stripe delivered this promptly).
        await billing_service.process_stripe_event(
            session,
            event=_subscription_event(
                event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
                status="active", sub_id=sub, created=base + 3600,
            ),
        )
        await session.commit()

        row = await session.get(WorkspaceBilling, ws)
        assert row is not None and row.status == "active"

        # A stale invoice.payment_failed — older than the applied "active"
        # event, e.g. a delayed retry of an earlier failed attempt that has
        # since been resolved — arrives late.
        stale_failed = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "invoice.payment_failed",
            "created": base,
            "data": {"object": {"id": f"in_{uuid.uuid4().hex[:10]}", "subscription": sub}},
        }
        result = await billing_service.process_stripe_event(session, event=stale_failed)
        await session.commit()
        assert result["status"] == "processed"

        await session.refresh(row)
        assert row.status == "active", (
            "a stale, delayed payment-failure event must not revoke "
            "entitlement that a newer applied event already confirmed"
        )
        assert billing_service.is_entitled(row, billing_enabled=True) is True


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


@pytest.mark.asyncio
async def test_concurrent_stale_payment_failure_does_not_overwrite_a_committed_active_state(
    billing_on,
):
    """Codex P1 on 7c07137: the payment-failure branch read WorkspaceBilling
    without FOR UPDATE before running its own freshness comparison. Under
    genuine concurrency — two separate transactions, not just two events in
    one session — an older invoice.payment_failed transaction's freshness
    check can run before a newer customer.subscription.updated "active"
    transaction's receipt has committed, so it correctly sees nothing to
    compare against, decides "not stale", and queues an unconditional
    status="past_due" write. That write's flush() only *incidentally* blocks
    on the active transaction's row lock (any UPDATE does); by the time it's
    unblocked and applied, the decision to overwrite was already made on
    stale information, so it clobbers the now-committed "active" status with
    "past_due" regardless of true event order. The freshness read must
    happen only *after* acquiring the same row lock _apply_subscription
    takes (via ensure_workspace_billing(..., for_update=True)), so a
    concurrent writer is forced to serialize behind the commit it needs to
    see before it decides anything.
    """
    async with AsyncSessionLocal() as setup:
        ws = await _workspace(setup)
        sub = f"sub_{uuid.uuid4().hex[:10]}"
        # Seed the row — with stripe_subscription_id already committed, so
        # the payment-failure branch's lookup-by-subscription-id finds it
        # regardless of which transaction commits first — so both sides hit
        # the SELECT ... FOR UPDATE path.
        seeded = await billing_service.ensure_workspace_billing(setup, workspace_id=ws)
        seeded.stripe_subscription_id = sub
        await setup.commit()

    base = int(datetime.now(UTC).timestamp())
    active_session = AsyncSessionLocal()
    failed_session = AsyncSessionLocal()
    try:
        active_event = _subscription_event(
            event_id=f"evt_{uuid.uuid4().hex[:12]}", workspace_id=ws,
            status="active", sub_id=sub, created=base + 3600,
        )
        # active_session processes the newer event and holds its row lock
        # open (uncommitted) — exactly the window the race needs.
        await billing_service.process_stripe_event(active_session, event=active_event)

        failed_event = {
            "id": f"evt_{uuid.uuid4().hex[:12]}",
            "type": "invoice.payment_failed",
            "created": base,
            "data": {"object": {"id": f"in_{uuid.uuid4().hex[:10]}", "subscription": sub}},
        }
        failed_task = asyncio.create_task(
            billing_service.process_stripe_event(failed_session, event=failed_event)
        )
        await asyncio.sleep(0.2)

        await active_session.commit()
        await asyncio.wait_for(failed_task, timeout=5)
        await failed_session.commit()

        async with AsyncSessionLocal() as verify:
            row = await verify.get(WorkspaceBilling, ws)
            assert row is not None
            assert row.status == "active", (
                "a payment-failure transaction racing a newer active "
                "transaction must not overwrite the committed active state "
                "once its own freshness check can actually see it"
            )
    finally:
        await active_session.close()
        await failed_session.close()
