"""Stripe webhook ingress — signature verified, idempotent, owner-session writes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.core.audit import audit
from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services import billing as billing_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict:
    if not get_settings().billing_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="billing is not enabled",
        )
    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing Stripe-Signature header",
        )
    payload = await request.body()
    try:
        event = billing_service.construct_stripe_event(
            payload=payload, sig_header=stripe_signature
        )
        async with AsyncSessionLocal() as session:
            result = await billing_service.process_stripe_event(session, event=event)
            await session.commit()
    except billing_service.BillingError as exc:
        code = (
            status.HTTP_400_BAD_REQUEST
            if exc.code in {"invalid_signature", "invalid_payload", "invalid_event"}
            else status.HTTP_422_UNPROCESSABLE_ENTITY
        )
        logger.warning(
            "stripe_webhook_rejected",
            extra={"code": exc.code, "detail": exc.message},
        )
        raise HTTPException(status_code=code, detail=exc.message) from exc

    audit(
        request,
        "stripe_webhook_received",
        event_id=result.get("event_id"),
        event_type=result.get("event_type"),
        webhook_status=result.get("status"),
    )
    return result
