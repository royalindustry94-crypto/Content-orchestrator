"""Pydantic schemas for the worker registry (Workstream 1).

Capability payloads are versioned (`protocol_version`) so future protocol
upgrades can be negotiated: the server validates the version against the
set it supports and echoes the accepted version back in the registration
response. A worker sending an unsupported version is rejected loudly
(422), never silently downgraded.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WorkerStatus


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
