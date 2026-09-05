from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    priority_tier: int | None = Field(default=None, ge=0, le=10)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    priority_tier: int = 0
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ContentProfileInput(BaseModel):
    service_mode: str = Field(pattern="^(own|client)$")
    business_name: str = Field(min_length=1, max_length=200)
    offer: str = Field(min_length=1, max_length=1000)
    target_audience: str = Field(min_length=1, max_length=1000)
    brand_voice: str = Field(min_length=1, max_length=500)
    target_platform: str = Field(min_length=1, max_length=80)
    content_goal: str = Field(min_length=1, max_length=1000)
    default_length_seconds: int = Field(default=60, ge=1, le=3600)

    @field_validator(
        "service_mode",
        "business_name",
        "offer",
        "target_audience",
        "brand_voice",
        "target_platform",
        "content_goal",
        mode="before",
    )
    @classmethod
    def strip_text(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ContentProfileOut(ContentProfileInput):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: uuid.UUID
    created_by: uuid.UUID | None
    updated_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
