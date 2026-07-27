from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SpendOut(BaseModel):
    workspace_id: uuid.UUID
    daily_cap_usd: float | None
    monthly_cap_usd: float | None
    daily_used_usd: float
    monthly_used_usd: float
    reserved_usd: float
    has_spend_history: bool
    cap_id: uuid.UUID | None


class SpendUpdateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    daily_cap_usd: float | None = Field(default=None, ge=0)
    monthly_cap_usd: float | None = Field(default=None, ge=0)
