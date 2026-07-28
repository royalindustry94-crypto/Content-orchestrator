from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BillingOut(BaseModel):
    workspace_id: uuid.UUID
    plan: str
    status: str
    entitled: bool
    billing_enabled: bool
    stripe_customer_id: str | None
    stripe_subscription_id: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool


class CheckoutOut(BaseModel):
    checkout_url: str
    session_id: str
    workspace_id: uuid.UUID


class CheckoutIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Optional override; defaults to the authenticated user's email.
    customer_email: str | None = Field(default=None, max_length=320)
