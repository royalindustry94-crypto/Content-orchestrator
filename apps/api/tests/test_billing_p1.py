"""P-001 Stripe billing + entitlement tests (mocked Stripe SDK)."""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.billing import WorkspaceBilling
from app.services import billing as billing_service


@pytest.fixture
def billing_on(monkeypatch):
    monkeypatch.setenv("BILLING_ENABLED", "true")
    monkeypatch.setenv("STRIPE_SECRET_KEY", "sk_test_audit")
    monkeypatch.setenv("STRIPE_WEBHOOK_SECRET", "whsec_audit")
    monkeypatch.setenv("STRIPE_PRICE_ID_PRO", "price_pro_audit")
    monkeypatch.setenv(
        "STRIPE_CHECKOUT_SUCCESS_URL", "http://localhost:5173/billing/success"
    )
    monkeypatch.setenv(
        "STRIPE_CHECKOUT_CANCEL_URL", "http://localhost:5173/billing/cancel"
    )
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("BILLING_ENABLED", raising=False)
    monkeypatch.delenv("STRIPE_SECRET_KEY", raising=False)
    monkeypatch.delenv("STRIPE_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("STRIPE_PRICE_ID_PRO", raising=False)
    monkeypatch.delenv("STRIPE_CHECKOUT_SUCCESS_URL", raising=False)
    monkeypatch.delenv("STRIPE_CHECKOUT_CANCEL_URL", raising=False)
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_billing_status_when_disabled(client, new_user):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Free Beta"})
    ws_id = ws.json()["id"]
    res = await client.get(f"/workspaces/{ws_id}/billing", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["billing_enabled"] is False
    assert body["entitled"] is True
    assert body["plan"] == "none"


@pytest.mark.asyncio
async def test_checkout_requires_billing_enabled(client, new_user):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "No Bill"})
    res = await client.post(
        f"/workspaces/{ws.json()['id']}/billing/checkout",
        headers=headers,
        json={},
    )
    assert res.status_code == 503


@pytest.mark.asyncio
async def test_checkout_creates_session(client, new_user, billing_on):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Pro Bound"})
    ws_id = ws.json()["id"]

    suffix = uuid.uuid4().hex[:8]
    fake_customer = {"id": f"cus_test_{suffix}"}
    fake_session = {
        "id": f"cs_test_{suffix}",
        "url": f"https://checkout.stripe.test/cs_test_{suffix}",
    }

    with (
        patch("app.services.billing.stripe.Customer.create", return_value=fake_customer),
        patch(
            "app.services.billing.stripe.checkout.Session.create",
            return_value=fake_session,
        ),
    ):
        res = await client.post(
            f"/workspaces/{ws_id}/billing/checkout",
            headers=headers,
            json={},
        )
    assert res.status_code == 200, res.text
    assert res.json()["checkout_url"].startswith("https://checkout.stripe.test/")
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, uuid.UUID(ws_id))
        assert row is not None
        assert row.stripe_customer_id == fake_customer["id"]


@pytest.mark.asyncio
async def test_webhook_checkout_completed_and_idempotent(billing_on):
    workspace_id = uuid.uuid4()
    # Seed workspace + profile for FK
    from sqlalchemy import text

    async with AsyncSessionLocal() as session:
        user_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO profiles (id, email) VALUES (:id, :email) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO workspaces (id, name, created_by) VALUES (:id, :name, :by)"
            ),
            {"id": str(workspace_id), "name": "Bill WS", "by": str(user_id)},
        )
        await session.commit()

    event = {
        "id": f"evt_test_checkout_{uuid.uuid4().hex}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": f"cs_{uuid.uuid4().hex[:8]}",
                "customer": f"cus_wh_{uuid.uuid4().hex[:8]}",
                "subscription": f"sub_wh_{uuid.uuid4().hex[:8]}",
                "client_reference_id": str(workspace_id),
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }
    async with AsyncSessionLocal() as session:
        first = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
    assert first["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        # H-2: checkout links customer/subscription only — no entitlement yet.
        assert row.plan == "none"
        assert row.status == "inactive"
        assert row.stripe_customer_id.startswith("cus_wh_")
        assert row.stripe_subscription_id.startswith("sub_wh_")
        assert not billing_service.is_entitled(row, billing_enabled=True)
        second = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
    assert second["status"] == "duplicate"

    # Entitlement arrives only via subscription lifecycle with active/trialing.
    sub_event = {
        "id": f"evt_test_sub_{uuid.uuid4().hex}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": event["data"]["object"]["subscription"],
                "customer": event["data"]["object"]["customer"],
                "status": "active",
                "current_period_end": 1_900_000_000,
                "cancel_at_period_end": False,
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }
    async with AsyncSessionLocal() as session:
        entitled = await billing_service.process_stripe_event(session, event=sub_event)
        await session.commit()
    assert entitled["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        assert row.plan == "pro"
        assert row.status == "active"
        assert billing_service.is_entitled(row, billing_enabled=True)


@pytest.mark.asyncio
async def test_content_job_requires_entitlement_when_billing_on(
    client, new_user, billing_on
):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Paywall"})
    ws_id = ws.json()["id"]
    blocked = await client.post(
        f"/workspaces/{ws_id}/content-jobs",
        headers=headers,
        json={"topic": "should pay first"},
    )
    assert blocked.status_code == 402

    async with AsyncSessionLocal() as session:
        await billing_service.ensure_workspace_billing(
            session, workspace_id=uuid.UUID(ws_id)
        )
        row = await session.get(WorkspaceBilling, uuid.UUID(ws_id))
        assert row is not None
        row.plan = "pro"
        row.status = "active"
        await session.commit()

    allowed = await client.post(
        f"/workspaces/{ws_id}/content-jobs",
        headers=headers,
        json={"topic": "entitled topic", "script_body": "draft"},
    )
    assert allowed.status_code == 201, allowed.text


@pytest.mark.asyncio
async def test_billing_idor(client, new_user, billing_on):
    a = new_user
    # second user
    email = f"{uuid.uuid4()}@ex.com"
    signup = await client.post(
        "/auth/signup", json={"email": email, "password": "securepass1-beta"}
    )
    hb = {"Authorization": f"Bearer {signup.json()['access_token']}"}
    _uid, _tok, ha = a
    ws = await client.post("/workspaces", headers=ha, json={"name": "Private Bill"})
    ws_id = ws.json()["id"]
    denied = await client.get(f"/workspaces/{ws_id}/billing", headers=hb)
    assert denied.status_code == 403


async def _seed_workspace() -> uuid.UUID:
    from sqlalchemy import text

    workspace_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO profiles (id, email) VALUES (:id, :email) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO workspaces (id, name, created_by) VALUES (:id, :name, :by)"
            ),
            {"id": str(workspace_id), "name": "Bill WS", "by": str(user_id)},
        )
        await session.commit()
    return workspace_id


@pytest.mark.asyncio
async def test_webhook_subscription_updated_and_canceled(billing_on):
    workspace_id = await _seed_workspace()
    sub_id = f"sub_lifecycle_{uuid.uuid4().hex[:8]}"
    cust_id = f"cus_lifecycle_{uuid.uuid4().hex[:8]}"
    period_end = 1_900_000_000

    async with AsyncSessionLocal() as session:
        await billing_service.ensure_workspace_billing(
            session, workspace_id=workspace_id
        )
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        row.stripe_customer_id = cust_id
        row.stripe_subscription_id = sub_id
        row.plan = "pro"
        row.status = "active"
        await session.commit()

    updated = {
        "id": f"evt_sub_upd_{uuid.uuid4().hex}",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": sub_id,
                "customer": cust_id,
                "status": "past_due",
                "current_period_end": period_end,
                "cancel_at_period_end": True,
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }
    async with AsyncSessionLocal() as session:
        result = await billing_service.process_stripe_event(session, event=updated)
        await session.commit()
    assert result["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        assert row.status == "past_due"
        assert row.plan == "pro"
        assert row.cancel_at_period_end is True
        assert not billing_service.is_entitled(row, billing_enabled=True)

    deleted = {
        "id": f"evt_sub_del_{uuid.uuid4().hex}",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": sub_id,
                "customer": cust_id,
                "status": "canceled",
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }
    async with AsyncSessionLocal() as session:
        result = await billing_service.process_stripe_event(session, event=deleted)
        await session.commit()
    assert result["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        assert row.status == "canceled"
        assert row.plan == "none"


@pytest.mark.asyncio
async def test_webhook_invoice_payment_failed(billing_on):
    workspace_id = await _seed_workspace()
    sub_id = f"sub_fail_{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        await billing_service.ensure_workspace_billing(
            session, workspace_id=workspace_id
        )
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        row.stripe_subscription_id = sub_id
        row.plan = "pro"
        row.status = "active"
        await session.commit()

    event = {
        "id": f"evt_inv_fail_{uuid.uuid4().hex}",
        "type": "invoice.payment_failed",
        "data": {"object": {"subscription": sub_id}},
    }
    async with AsyncSessionLocal() as session:
        result = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
    assert result["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        assert row.status == "past_due"


@pytest.mark.asyncio
async def test_webhook_http_rejects_bad_signature(client, billing_on):
    res = await client.post(
        "/webhooks/stripe",
        content=b'{"id":"evt_x"}',
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_webhook_rejection_is_audit_logged(client, billing_on, caplog):
    """INFO-2: a rejected webhook (bad signature) is a potential
    attack/misconfiguration signal and must land in the audit trail, not
    just general application logs.
    """
    with caplog.at_level("INFO", logger="audit"):
        res = await client.post(
            "/webhooks/stripe",
            content=b'{"id":"evt_x"}',
            headers={"Stripe-Signature": "t=1,v1=deadbeef"},
        )
    assert res.status_code == 400
    record = next(
        r
        for r in caplog.records
        if r.name == "audit" and r.getMessage() == "stripe_webhook_rejected"
    )
    assert record.audit_event == "stripe_webhook_rejected"
    assert record.code == "invalid_signature"


@pytest.mark.asyncio
async def test_checkout_already_entitled(client, new_user, billing_on):
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Already Pro"})
    ws_id = ws.json()["id"]
    async with AsyncSessionLocal() as session:
        await billing_service.ensure_workspace_billing(
            session, workspace_id=uuid.UUID(ws_id)
        )
        row = await session.get(WorkspaceBilling, uuid.UUID(ws_id))
        assert row is not None
        row.plan = "pro"
        row.status = "active"
        await session.commit()
    res = await client.post(
        f"/workspaces/{ws_id}/billing/checkout",
        headers=headers,
        json={},
    )
    assert res.status_code == 409


@pytest.mark.asyncio
async def test_checkout_customer_create_failure_raises_clean_billing_error(
    client, new_user, billing_on
):
    """LOW-1: a Stripe failure on Customer.create must surface as a clean
    503 (BillingError), not an unhandled 500, and must not leave a
    half-applied stripe_customer_id behind for a retry to skip past.
    """
    import stripe

    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Cust Fail"})
    ws_id = ws.json()["id"]
    # Seed the billing row via a separately-committed transaction, matching
    # production: GET /billing always seeds it first (routes/billing.py),
    # so by the time checkout runs the row already exists in the DB.
    await client.get(f"/workspaces/{ws_id}/billing", headers=headers)

    with patch(
        "app.services.billing.stripe.Customer.create",
        side_effect=stripe.error.StripeError("network blip"),
    ):
        res = await client.post(
            f"/workspaces/{ws_id}/billing/checkout",
            headers=headers,
            json={},
        )
    assert res.status_code == 503, res.text

    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, uuid.UUID(ws_id))
        assert row is not None
        assert row.stripe_customer_id is None


@pytest.mark.asyncio
async def test_checkout_session_create_failure_does_not_persist_customer_id(
    client, new_user, billing_on
):
    """LOW-1: if Customer.create succeeds but Session.create then fails, the
    route must not commit the half-applied stripe_customer_id — otherwise a
    retry would skip Customer.create (branch already covered by
    test_checkout_reuses_existing_stripe_customer_id) while the checkout
    itself never actually completed.
    """
    import stripe

    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Sess Fail"})
    ws_id = ws.json()["id"]
    await client.get(f"/workspaces/{ws_id}/billing", headers=headers)
    fake_customer = {"id": f"cus_test_{uuid.uuid4().hex[:8]}"}

    with (
        patch(
            "app.services.billing.stripe.Customer.create",
            return_value=fake_customer,
        ),
        patch(
            "app.services.billing.stripe.checkout.Session.create",
            side_effect=stripe.error.StripeError("stripe 5xx"),
        ),
    ):
        res = await client.post(
            f"/workspaces/{ws_id}/billing/checkout",
            headers=headers,
            json={},
        )
    assert res.status_code == 503, res.text

    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, uuid.UUID(ws_id))
        assert row is not None
        assert row.stripe_customer_id is None, (
            "the route only commits after create_checkout_session returns "
            "successfully, so a failure between the two Stripe calls must "
            "roll back the customer id rather than persist it half-applied"
        )


@pytest.mark.asyncio
async def test_checkout_reuses_existing_stripe_customer_id(client, new_user, billing_on):
    """The existing-customer branch: Customer.create must not be called
    again once stripe_customer_id is already set on the billing row.
    """
    _uid, _tok, headers = new_user
    ws = await client.post("/workspaces", headers=headers, json={"name": "Reuse Cust"})
    ws_id = ws.json()["id"]
    existing_customer_id = f"cus_existing_{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as session:
        row = await billing_service.ensure_workspace_billing(
            session, workspace_id=uuid.UUID(ws_id)
        )
        row.stripe_customer_id = existing_customer_id
        await session.commit()

    fake_session = {
        "id": f"cs_test_{uuid.uuid4().hex[:8]}",
        "url": "https://checkout.stripe.test/cs_test_reuse",
    }
    with (
        patch("app.services.billing.stripe.Customer.create") as create_customer,
        patch(
            "app.services.billing.stripe.checkout.Session.create",
            return_value=fake_session,
        ) as create_session,
    ):
        res = await client.post(
            f"/workspaces/{ws_id}/billing/checkout",
            headers=headers,
            json={},
        )
    assert res.status_code == 200, res.text
    create_customer.assert_not_called()
    create_session.assert_called_once()
    assert create_session.call_args.kwargs["customer"] == existing_customer_id
