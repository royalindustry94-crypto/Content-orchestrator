"""Workspace billing (Stripe Checkout + entitlement status)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import require_workspace_admin, require_workspace_member
from app.core.config import get_settings
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.db.session import AsyncSessionLocal
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.billing import BillingOut, CheckoutIn, CheckoutOut
from app.services import billing as billing_service

router = APIRouter(prefix="/workspaces/{workspace_id}/billing", tags=["billing"])


@router.get("", response_model=BillingOut)
async def get_billing(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> BillingOut:
    # Seed row via owner session so admin insert RLS is not required for reads.
    async with AsyncSessionLocal() as owner:
        await billing_service.ensure_workspace_billing(owner, workspace_id=workspace_id)
        await owner.commit()
    ent = await billing_service.get_entitlement(db, workspace_id=workspace_id)
    return BillingOut(
        workspace_id=ent.workspace_id,
        plan=ent.plan,
        status=ent.status,
        entitled=ent.entitled,
        billing_enabled=ent.billing_enabled,
        stripe_customer_id=ent.stripe_customer_id,
        stripe_subscription_id=ent.stripe_subscription_id,
        current_period_end=ent.current_period_end,
        cancel_at_period_end=ent.cancel_at_period_end,
    )


@router.post("/checkout", response_model=CheckoutOut)
async def create_checkout(
    workspace_id: uuid.UUID,
    payload: CheckoutIn,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    _membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> CheckoutOut:
    if not get_settings().billing_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="billing is not enabled",
        )
    try:
        async with AsyncSessionLocal() as session:
            result = await billing_service.create_checkout_session(
                session,
                workspace_id=workspace_id,
                customer_email=payload.customer_email or user.email,
            )
            await session.commit()
    except billing_service.BillingError as exc:
        code = (
            status.HTTP_409_CONFLICT
            if exc.code == "already_entitled"
            else status.HTTP_400_BAD_REQUEST
        )
        if exc.code == "billing_misconfigured":
            code = status.HTTP_503_SERVICE_UNAVAILABLE
        raise HTTPException(status_code=code, detail=exc.message) from exc

    audit(
        request,
        "billing_checkout_created",
        workspace_id=str(workspace_id),
        session_id=result.session_id,
    )
    return CheckoutOut(
        checkout_url=result.checkout_url,
        session_id=result.session_id,
        workspace_id=result.workspace_id,
    )
