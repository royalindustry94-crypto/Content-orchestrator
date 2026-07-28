"""Stripe Checkout + workspace entitlement service.

When BILLING_ENABLED=false the product path behaves as Private Beta (P0).
When true, Checkout creates a Stripe session and webhooks mirror subscription
state into workspace_billing; content-jobs require an active/trialing Pro plan.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.models.billing import BillingWebhookEvent, WorkspaceBilling

logger = logging.getLogger(__name__)

ACTIVE_STATUSES = frozenset({"active", "trialing"})
PRO_PLAN = "pro"


class BillingError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CheckoutResult:
    checkout_url: str
    session_id: str
    workspace_id: uuid.UUID


@dataclass(frozen=True)
class Entitlement:
    workspace_id: uuid.UUID
    plan: str
    status: str
    entitled: bool
    billing_enabled: bool
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool


def _require_billing_config(settings: Settings) -> None:
    if not settings.billing_enabled:
        raise BillingError("billing_disabled", "billing is not enabled")
    missing = [
        name
        for name, value in (
            ("STRIPE_SECRET_KEY", settings.stripe_secret_key),
            ("STRIPE_WEBHOOK_SECRET", settings.stripe_webhook_secret),
            ("STRIPE_PRICE_ID_PRO", settings.stripe_price_id_pro),
            ("STRIPE_CHECKOUT_SUCCESS_URL", settings.stripe_checkout_success_url),
            ("STRIPE_CHECKOUT_CANCEL_URL", settings.stripe_checkout_cancel_url),
        )
        if not value
    ]
    if missing:
        raise BillingError(
            "billing_misconfigured",
            f"billing enabled but missing required settings: {', '.join(missing)}",
        )


def _configure_stripe(settings: Settings) -> None:
    _require_billing_config(settings)
    stripe.api_key = settings.stripe_secret_key


async def ensure_workspace_billing(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> WorkspaceBilling:
    row = await session.get(WorkspaceBilling, workspace_id)
    if row is not None:
        return row
    row = WorkspaceBilling(
        workspace_id=workspace_id,
        plan="none",
        status="inactive",
    )
    session.add(row)
    await session.flush()
    return row


def is_entitled(row: WorkspaceBilling | None, *, billing_enabled: bool) -> bool:
    if not billing_enabled:
        return True
    if row is None:
        return False
    return row.plan == PRO_PLAN and row.status in ACTIVE_STATUSES


async def get_entitlement(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> Entitlement:
    settings = get_settings()
    row = await ensure_workspace_billing(session, workspace_id=workspace_id)
    return Entitlement(
        workspace_id=workspace_id,
        plan=row.plan,
        status=row.status,
        entitled=is_entitled(row, billing_enabled=settings.billing_enabled),
        billing_enabled=settings.billing_enabled,
        stripe_customer_id=row.stripe_customer_id,
        stripe_subscription_id=row.stripe_subscription_id,
        current_period_end=row.current_period_end,
        cancel_at_period_end=row.cancel_at_period_end,
    )


async def require_entitlement_for_workspace(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> None:
    """Raise BillingError when billing is on and the workspace is not entitled."""
    settings = get_settings()
    if not settings.billing_enabled:
        return
    row = await session.get(WorkspaceBilling, workspace_id)
    if not is_entitled(row, billing_enabled=True):
        raise BillingError(
            "not_entitled",
            "workspace requires an active Pro subscription to create content jobs",
        )


async def create_checkout_session(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    customer_email: str | None,
) -> CheckoutResult:
    settings = get_settings()
    _configure_stripe(settings)
    billing = await ensure_workspace_billing(session, workspace_id=workspace_id)

    if is_entitled(billing, billing_enabled=True):
        raise BillingError("already_entitled", "workspace already has an active Pro plan")

    if not billing.stripe_customer_id:
        customer = stripe.Customer.create(
            email=customer_email,
            metadata={"workspace_id": str(workspace_id)},
        )
        billing.stripe_customer_id = customer["id"]
        await session.flush()

    checkout = stripe.checkout.Session.create(
        mode="subscription",
        customer=billing.stripe_customer_id,
        line_items=[{"price": settings.stripe_price_id_pro, "quantity": 1}],
        success_url=settings.stripe_checkout_success_url,
        cancel_url=settings.stripe_checkout_cancel_url,
        client_reference_id=str(workspace_id),
        metadata={"workspace_id": str(workspace_id)},
        subscription_data={"metadata": {"workspace_id": str(workspace_id)}},
    )
    url = checkout.get("url")
    if not url:
        raise BillingError("checkout_failed", "Stripe Checkout session missing url")
    logger.info(
        "stripe_checkout_created",
        extra={
            "workspace_id": str(workspace_id),
            "session_id": checkout["id"],
            "customer_id": billing.stripe_customer_id,
        },
    )
    return CheckoutResult(
        checkout_url=url,
        session_id=checkout["id"],
        workspace_id=workspace_id,
    )


def _period_end_from_subscription(sub: dict) -> datetime | None:
    raw = sub.get("current_period_end")
    if raw is None:
        return None
    return datetime.fromtimestamp(int(raw), tz=UTC)


async def _apply_subscription(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    subscription: dict,
) -> None:
    billing = await ensure_workspace_billing(session, workspace_id=workspace_id)
    billing.stripe_subscription_id = subscription.get("id") or billing.stripe_subscription_id
    customer = subscription.get("customer")
    if isinstance(customer, str):
        billing.stripe_customer_id = customer
    elif isinstance(customer, dict) and customer.get("id"):
        billing.stripe_customer_id = customer["id"]

    status = str(subscription.get("status") or "inactive")
    billing.status = status
    if status in ACTIVE_STATUSES:
        billing.plan = PRO_PLAN
    elif status == "canceled":
        billing.plan = "none"
    elif status in {"past_due", "unpaid", "incomplete"}:
        # Keep Pro plan marker so ops can see what lapsed; entitlement is false.
        billing.plan = PRO_PLAN
    billing.current_period_end = _period_end_from_subscription(subscription)
    billing.cancel_at_period_end = bool(subscription.get("cancel_at_period_end") or False)
    await session.flush()


async def _workspace_id_from_metadata(obj: dict) -> uuid.UUID | None:
    meta = obj.get("metadata") or {}
    raw = meta.get("workspace_id") or obj.get("client_reference_id")
    if not raw:
        return None
    try:
        return uuid.UUID(str(raw))
    except ValueError:
        return None


async def process_stripe_event(session: AsyncSession, *, event: dict) -> dict:
    """Apply one verified Stripe event. Idempotent on stripe_event_id."""
    event_id = event.get("id")
    event_type = event.get("type")
    if not event_id or not event_type:
        raise BillingError("invalid_event", "Stripe event missing id or type")

    existing = (
        await session.execute(
            select(BillingWebhookEvent).where(
                BillingWebhookEvent.stripe_event_id == event_id
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        logger.info(
            "stripe_webhook_duplicate",
            extra={"stripe_event_id": event_id, "event_type": event_type},
        )
        return {"status": "duplicate", "event_id": event_id, "event_type": event_type}

    data_object = (event.get("data") or {}).get("object") or {}
    workspace_id = await _workspace_id_from_metadata(data_object)

    if event_type == "checkout.session.completed":
        if workspace_id is None:
            raise BillingError("missing_workspace", "checkout session missing workspace_id")
        sub_id = data_object.get("subscription")
        customer_id = data_object.get("customer")
        billing = await ensure_workspace_billing(session, workspace_id=workspace_id)
        if isinstance(customer_id, str):
            billing.stripe_customer_id = customer_id
        if isinstance(sub_id, str):
            billing.stripe_subscription_id = sub_id
        billing.plan = PRO_PLAN
        billing.status = "active"
        await session.flush()
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        if workspace_id is None:
            sub_id = data_object.get("id")
            cust = data_object.get("customer")
            row = None
            if isinstance(sub_id, str):
                row = (
                    await session.execute(
                        select(WorkspaceBilling).where(
                            WorkspaceBilling.stripe_subscription_id == sub_id
                        )
                    )
                ).scalar_one_or_none()
            if row is None and isinstance(cust, str):
                row = (
                    await session.execute(
                        select(WorkspaceBilling).where(
                            WorkspaceBilling.stripe_customer_id == cust
                        )
                    )
                ).scalar_one_or_none()
            if row is None:
                raise BillingError(
                    "unknown_subscription",
                    "subscription event could not be mapped to a workspace",
                )
            workspace_id = row.workspace_id
        await _apply_subscription(
            session, workspace_id=workspace_id, subscription=data_object
        )
    elif event_type == "invoice.payment_failed":
        sub = data_object.get("subscription")
        if isinstance(sub, str):
            row = (
                await session.execute(
                    select(WorkspaceBilling).where(
                        WorkspaceBilling.stripe_subscription_id == sub
                    )
                )
            ).scalar_one_or_none()
            if row is not None:
                row.status = "past_due"
                workspace_id = row.workspace_id
                await session.flush()
    else:
        logger.info(
            "stripe_webhook_ignored",
            extra={"stripe_event_id": event_id, "event_type": event_type},
        )

    session.add(
        BillingWebhookEvent(
            id=uuid.uuid4(),
            stripe_event_id=event_id,
            event_type=event_type,
            workspace_id=workspace_id,
            payload=event,
        )
    )
    await session.flush()
    logger.info(
        "stripe_webhook_processed",
        extra={
            "stripe_event_id": event_id,
            "event_type": event_type,
            "workspace_id": str(workspace_id) if workspace_id else None,
        },
    )
    return {
        "status": "processed",
        "event_id": event_id,
        "event_type": event_type,
        "workspace_id": str(workspace_id) if workspace_id else None,
    }


def construct_stripe_event(*, payload: bytes, sig_header: str) -> dict:
    settings = get_settings()
    _configure_stripe(settings)
    assert settings.stripe_webhook_secret is not None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as exc:
        raise BillingError("invalid_signature", "invalid Stripe webhook signature") from exc
    except Exception as exc:  # noqa: BLE001
        raise BillingError("invalid_payload", f"invalid Stripe webhook payload: {exc}") from exc
    if hasattr(event, "to_dict"):
        return event.to_dict()
    return dict(event)
