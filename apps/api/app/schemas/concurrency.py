"""Schemas for concurrency limits and provider budgets (WS4)."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BackpressureState


class ConcurrencyLimitsUpdate(BaseModel):
    max_concurrent_assignments: int | None = Field(default=None, ge=1)
    max_per_scheduler_tick: int | None = Field(default=None, ge=1)
    queue_soft_limit: int | None = Field(default=None, ge=1)
    queue_hard_limit: int | None = Field(default=None, ge=1)


class ConcurrencyLimitsOut(BaseModel):
    workspace_id: uuid.UUID
    max_concurrent_assignments: int
    max_per_scheduler_tick: int
    queue_soft_limit: int
    queue_hard_limit: int
    pending_depth: int
    in_flight: int
    backpressure_state: BackpressureState


class ProviderBudgetUpsert(BaseModel):
    max_concurrent: int = Field(ge=1)


class ProviderBudgetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    provider: str
    max_concurrent: int
    created_at: datetime
    updated_at: datetime
