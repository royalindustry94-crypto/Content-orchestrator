"""Schemas for Private Beta content jobs + review desk APIs."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentJobCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
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


class ReviewGateEditIn(BaseModel):
    """At least one script field must be given; omitted fields keep their
    current value (see `content_desk.edit_review_gate_content`)."""

    script_hook: str | None = Field(default=None, max_length=2000)
    script_body: str | None = Field(default=None, max_length=50000)
    script_cta: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _require_at_least_one_field(self) -> ReviewGateEditIn:
        if self.script_hook is None and self.script_body is None and self.script_cta is None:
            raise ValueError(
                "at least one of script_hook, script_body, script_cta must be provided"
            )
        return self


class ReviewDecisionIn(BaseModel):
    approved: bool
    notes: str | None = Field(default=None, max_length=5000)
    # Optional: the content_version_id the caller's client had loaded when
    # the reviewer chose to approve/reject. If given and it no longer
    # matches the gate's current snapshot (e.g. an editor changed the
    # content while this gate sat open in the reviewer's drawer), the
    # decision is rejected as a conflict rather than silently binding the
    # reviewer's decision to content they never actually saw.
    expected_content_version_id: uuid.UUID | None = None


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
