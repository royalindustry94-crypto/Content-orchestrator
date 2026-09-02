"""Pydantic schemas for the worker registry (Workstream 1).

Capability payloads are versioned (`protocol_version`) so future protocol
upgrades can be negotiated: the server validates the version against the
set it supports and echoes the accepted version back in the registration
response. A worker sending an unsupported version is rejected loudly
(422), never silently downgraded.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import StageAssignmentStatus, WorkerStatus


class ProviderCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    models: list[str] = Field(default_factory=list)
    max_concurrency: int = Field(default=1, ge=1, le=1000)


class CapabilitySpec(BaseModel):
    """Versioned capability declaration. `extra="forbid"` so unknown keys
    fail loudly instead of being silently dropped — a worker built for a
    future protocol version must bump `protocol_version`, not smuggle new
    fields into v1.
    """

    model_config = ConfigDict(extra="forbid")

    protocol_version: int = Field(ge=1)
    providers: list[ProviderCapability] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)


class WorkerProvisionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=200)
    supported_stages: list[str] = Field(default_factory=list)
    max_concurrency: int = Field(default=1, ge=1, le=1000)


class WorkerProvisionOut(BaseModel):
    """The ONLY response that ever contains a worker secret, returned once
    at provisioning. The secret is not recoverable afterwards — only
    rotation issues a new one.
    """

    worker_id: uuid.UUID
    credential_id: uuid.UUID
    worker_secret: str
    workspace_id: uuid.UUID


class WorkerRegisterIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported_stages: list[str] = Field(default_factory=list)
    capabilities: CapabilitySpec
    worker_version: str | None = Field(default=None, max_length=100)
    max_concurrency: int = Field(default=1, ge=1, le=1000)


class WorkerRegisterOut(BaseModel):
    worker_id: uuid.UUID
    status: WorkerStatus
    accepted_protocol_version: int


class WorkerHeartbeatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: WorkerStatus = WorkerStatus.ONLINE
    current_load: int = Field(default=0, ge=0)


class WorkerLogIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: str = Field(pattern="^(debug|info|warning|error|critical)$")
    message: str = Field(min_length=1, max_length=8000)
    pipeline_run_id: uuid.UUID | None = None
    assignment_id: uuid.UUID | None = None
    occurred_at: datetime | None = None
    context: dict = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def context_must_be_bounded(cls, value: dict) -> dict:
        if len(value) > 64:
            raise ValueError("context may contain at most 64 top-level keys")
        encoded = json.dumps(value, separators=(",", ":"), ensure_ascii=False).encode()
        if len(encoded) > 16 * 1024:
            raise ValueError("context must not exceed 16 KiB")

        def depth(item: object, level: int = 0) -> int:
            if isinstance(item, dict):
                return max((depth(child, level + 1) for child in item.values()), default=level)
            if isinstance(item, list):
                return max((depth(child, level + 1) for child in item), default=level)
            return level

        if depth(value) > 8:
            raise ValueError("context nesting must not exceed 8 levels")
        return value


class WorkerLogAccepted(BaseModel):
    id: uuid.UUID
    received_at: datetime


class WorkerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID | None
    name: str
    status: WorkerStatus
    liveness: str  # computed: healthy | suspect | dead
    drain: bool
    supported_stages: list[str]
    capabilities: dict | None
    worker_version: str | None
    max_concurrency: int
    current_load: int
    health_score: int
    last_heartbeat_at: datetime | None
    registered_at: datetime
    deregistered_at: datetime | None


class WorkerDrainIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drain: bool


class CredentialRotateOut(BaseModel):
    """New secret returned exactly once. The previous credential remains
    ACTIVE until `previous_expires_at` (rotation grace) so a fleet can
    switch over with zero downtime.
    """

    credential_id: uuid.UUID
    worker_secret: str
    previous_expires_at: datetime | None


class HeartbeatRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    worker_id: uuid.UUID
    status: WorkerStatus
    current_load: int
    heartbeat_at: datetime


class ClaimIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Optional idempotency token: a retried claim with the same token
    # returns the assignment already held rather than consuming a new one.
    claim_token: uuid.UUID | None = None


class ClaimedAssignmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: str
    pipeline_run_id: uuid.UUID
    attempt_number: int
    lease_expires_at: datetime | None
    correlation_id: uuid.UUID | None
    trace_id: str | None
    # Execution context for Draft Desk / generators (optional enrichment).
    workspace_id: uuid.UUID | None = None
    content_item_id: uuid.UUID | None = None
    topic: str | None = None
    target_length_seconds: int | None = None
    business_name: str | None = None
    offer: str | None = None
    target_audience: str | None = None
    brand_voice: str | None = None
    content_goal: str | None = None
    target_platform: str | None = None
    provider: str | None = None


class ClaimOut(BaseModel):
    assignment: ClaimedAssignmentOut | None
    outcome: str  # granted | no_work | capacity | ineligible
    reason: str


class LeaseOut(BaseModel):
    assignment_id: uuid.UUID
    status: StageAssignmentStatus
    lease_expires_at: datetime | None
    lease_extension_count: int
    attempt_number: int


class SubmitIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool
    result: dict | None = None
    error_message: str = ""
    provider_effect_key: str | None = Field(default=None, max_length=500)


class SubmitOut(BaseModel):
    assignment_id: uuid.UUID
    status: StageAssignmentStatus
    provider_effect_key: str | None = None
    provider_effect_created: bool | None = None
