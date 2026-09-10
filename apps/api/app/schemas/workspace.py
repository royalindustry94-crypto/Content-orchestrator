from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from app.models.content_profile import is_content_profile_complete


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
    """All fields optional — a step skipped in the guided wizard, or a
    field cleared in manual Settings editing, is a real, honest state
    (that default just won't be offered), not a validation error.
    """

    business_name: str | None = Field(default=None, max_length=200)
    offer: str | None = Field(default=None, max_length=2000)
    target_audience: str | None = Field(default=None, max_length=2000)
    brand_voice: str | None = Field(default=None, max_length=2000)
    target_platform: str | None = Field(default=None, max_length=100)
    content_goal: str | None = Field(default=None, max_length=2000)

    @field_validator(
        "business_name",
        "offer",
        "target_audience",
        "brand_voice",
        "target_platform",
        "content_goal",
    )
    @classmethod
    def strip_and_blank_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class ContentProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    workspace_id: uuid.UUID
    business_name: str | None
    offer: str | None
    target_audience: str | None
    brand_voice: str | None
    target_platform: str | None
    content_goal: str | None
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_complete(self) -> bool:
        """True once every field a first-time-setup wizard collects has a
        value — used by the frontend to decide whether to show "complete"
        or keep prompting. Not a backend-enforced gate on anything.
        """
        return is_content_profile_complete(self)
