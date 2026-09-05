"""API contracts for the provider-neutral Human Creative Director."""

from __future__ import annotations

import json
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class _BoundedPayload(BaseModel):
    @model_validator(mode="after")
    def bound_structured_payload(self):
        if len(json.dumps(self.model_dump(mode="json"), separators=(",", ":"))) > 64_000:
            raise ValueError("creative payload must not exceed 64 KB")
        return self


class CreativeBriefInput(_BoundedPayload):
    customer_request: str = Field(min_length=1, max_length=10_000)
    requirements: dict = Field(default_factory=dict)
    exclusions: list[str] = Field(default_factory=list, max_length=100)
    reference_notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("customer_request", "reference_notes", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CreativeProjectCreate(_BoundedPayload):
    title: str = Field(min_length=1, max_length=200)
    desired_outcome: str = Field(min_length=1, max_length=5_000)
    brief: CreativeBriefInput

    @field_validator("title", "desired_outcome", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class PromptPackInput(_BoundedPayload):
    brief_version_id: UUID
    target_tool: str | None = Field(default=None, max_length=100)
    prompt_spec: dict
    continuity_rules: list[str] = Field(default_factory=list, max_length=200)
    negative_prompts: list[str] = Field(default_factory=list, max_length=200)
    validation_checklist: list[str] = Field(default_factory=list, max_length=200)
    estimated_generation_count: int = Field(default=1, ge=1, le=1_000)

    @field_validator("target_tool", mode="before")
    @classmethod
    def strip_target_tool(cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @field_validator("prompt_spec")
    @classmethod
    def require_prompt_spec(cls, value: dict) -> dict:
        if not value:
            raise ValueError("prompt_spec must contain at least one instruction")
        return value


class PromptPackDecisionInput(BaseModel):
    approved: bool
    prompt_pack_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    notes: str | None = Field(default=None, max_length=5_000)


class CreativeBriefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    revision_number: int
    customer_request: str
    requirements: dict
    exclusions: list
    reference_notes: str | None
    fingerprint: str
    created_by: UUID | None
    created_at: datetime


class PromptPackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    brief_version_id: UUID
    revision_number: int
    target_tool: str | None
    prompt_spec: dict
    continuity_rules: list
    negative_prompts: list
    validation_checklist: list
    estimated_generation_count: int
    fingerprint: str
    created_by: UUID | None
    created_at: datetime


class PromptPackDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    project_id: UUID
    prompt_pack_version_id: UUID
    prompt_pack_fingerprint: str
    decision: str
    notes: str | None
    reviewer_id: UUID
    created_at: datetime


class CreativeProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    desired_outcome: str
    status: str
    version: int
    created_by: UUID | None
    updated_by: UUID | None
    created_at: datetime
    updated_at: datetime


class CreativeProjectDetail(BaseModel):
    project: CreativeProjectOut
    latest_brief: CreativeBriefOut
    latest_prompt_pack: PromptPackOut | None
    latest_decision: PromptPackDecisionOut | None
    approved_for_generation: bool
