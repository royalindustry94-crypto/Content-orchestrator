from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    daily_cap_usd: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)
    monthly_cap_usd: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=4)

    @field_validator("daily_cap_usd", "monthly_cap_usd", mode="before")
    @classmethod
    def _coerce_decimal(cls, value: object) -> object:
        if value is None or isinstance(value, Decimal):
            return value
        if isinstance(value, int | float | str):
            return Decimal(str(value))
        return value
