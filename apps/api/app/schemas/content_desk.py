"""Schemas for Private Beta content jobs + review desk APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ContentJobCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    business_name: str | None = Field(default=None, max_length=200)
    offer: str | None = Field(default=None, max_length=1000)
    target_audience: str | None = Field(default=None, max_length=1000)
    brand_voice: str | None = Field(default=None, max_length=500)
    content_goal: str | None = Field(default=None, max_length=1000)
    target_platform: str | None = Field(default=None, max_length=80)
    script_hook: str | None = Field(default=None, max_length=2000)
    script_body: str | None = Field(default=None, max_length=50000)
    script_cta: str | None = Field(default=None, max_length=2000)
    target_length_seconds: int | None = Field(default=None, ge=1, le=3600)
    idempotency_key: str | None = Field(default=None, min_length=1, max_length=200)


class ContentJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    content_item_id: uuid.UUID
    pipeline_run_id: uuid.UUID
    review_gate_id: uuid.UUID
    topic: str
    current_stage: str
    run_status: str
    gate_status: str


class ReviewDecisionIn(BaseModel):
    approved: bool
    content_version_id: uuid.UUID
    notes: str | None = Field(default=None, max_length=5000)


class ReviewGateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    pipeline_run_id: uuid.UUID
    content_item_id: uuid.UUID
    content_version_id: uuid.UUID | None
    topic: str
    stage: str
    status: str
    requested_at: datetime
    timeout_at: datetime | None
    decided_at: datetime | None
    decided_by: uuid.UUID | None
    script_hook: str | None
    script_body: str | None
    script_cta: str | None
    run_status: str
