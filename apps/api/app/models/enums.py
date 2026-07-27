"""Python-side mirrors of the Postgres ENUM types defined in the
Milestone 3 migrations. Each `name=` on a Postgres-side Enum column must
match the type name created in the migration.
"""

from __future__ import annotations

import enum


class ContentStage(str, enum.Enum):
    IDEA = "idea"
    SCRIPTING = "scripting"
    VOICEOVER = "voiceover"
    VISUALS = "visuals"
    RENDERING = "rendering"
    SEO = "seo"
    REVIEW = "review"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"


class ContentStatus(str, enum.Enum):
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


class PipelineRunStatus(str, enum.Enum):
    """Full pipeline_run_status enum (M3 + M4 paused/compensating/created)."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPENSATING = "compensating"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StageRunStatus(str, enum.Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AssetType(str, enum.Enum):
    SCRIPT = "script"
    AUDIO = "audio"
    VISUAL = "visual"
    RENDER = "render"


class AssetSource(str, enum.Enum):
    AI_GENERATED = "ai_generated"
    UPLOADED = "uploaded"


class AssetStatus(str, enum.Enum):
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"


class PublishJobStatus(str, enum.Enum):
    PENDING = "pending"
    PUBLISHING = "publishing"
    PUBLISHED = "published"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewDecisionValue(str, enum.Enum):
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ReservationStatus(str, enum.Enum):
    RESERVED = "reserved"
    COMMITTED = "committed"
    RELEASED = "released"


class ProviderCredentialStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class WebhookStatus(str, enum.Enum):
    RECEIVED = "received"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"


class DeadLetterStatus(str, enum.Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISCARDED = "discarded"


class ContentLineageRelationship(str, enum.Enum):
    TRANSLATED = "translated"
    REMIXED = "remixed"
    CLIPPED = "clipped"
    DERIVED = "derived"


# --- Milestone 4: orchestration ---

class WorkflowTransitionTrigger(str, enum.Enum):
    ON_SUCCESS = "on_success"
    ON_FAILURE = "on_failure"
    ON_REVIEW_APPROVED = "on_review_approved"
    ON_REVIEW_REJECTED = "on_review_rejected"


class OutboxEventStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    POISON = "poison"


class JobType(str, enum.Enum):
    STAGE = "stage"
    RETRY = "retry"
    STAGE_TIMEOUT = "stage_timeout"
    REVIEW_TIMEOUT = "review_timeout"
    RECURRING = "recurring"
    COMPENSATION = "compensation"


class JobScheduleStatus(str, enum.Enum):
    PENDING = "pending"
    LEASED = "leased"
    DONE = "done"
    CANCELLED = "cancelled"


class WorkerStatus(str, enum.Enum):
    ONLINE = "online"
    BUSY = "busy"
    DRAINING = "draining"
    OFFLINE = "offline"


class StageAssignmentStatus(str, enum.Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    ACKNOWLEDGED = "acknowledged"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ReviewGateStatus(str, enum.Enum):
    AWAITING = "awaiting"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    ESCALATED = "escalated"


# PipelineRunStatusV2 removed — use PipelineRunStatus (aligned with DB enum
# values from migration 0014: created/paused/compensating).


class PauseReason(str, enum.Enum):
    REVIEW_GATE = "review_gate"
    MANUAL = "manual"
    SPEND_HOLD = "spend_hold"


class WorkerCredentialStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class ClaimOutcome(str, enum.Enum):
    """Outcome of a worker's atomic claim attempt (WS2). Recorded on every
    attempt in stage_claim_audit. Only `granted` hands out work; the rest
    are normal, audited non-grants (never silent failures).
    """

    GRANTED = "granted"
    NO_WORK = "no_work"
    CAPACITY = "capacity"
    INELIGIBLE = "ineligible"


class RecoveryReason(str, enum.Enum):
    """Why an in-flight assignment was recovered (WS3)."""

    LEASE_EXPIRED = "lease_expired"
    WORKER_OFFLINE = "worker_offline"
    WORKER_DEREGISTERED = "worker_deregistered"
    WORKER_REVOKED = "worker_revoked"
    WORKER_RESTART = "worker_restart"
    MAX_LEASE_EXCEEDED = "max_lease_exceeded"


class RecoveryOutcome(str, enum.Enum):
    """Result of a recovery attempt (WS3)."""

    REQUEUED = "requeued"
    DEAD_LETTERED = "dead_lettered"
    SKIPPED = "skipped"


class BackpressureState(str, enum.Enum):
    """Per-workspace queue-depth back-pressure observation (WS4)."""

    NORMAL = "normal"
    PRESSURED = "pressured"
    THROTTLED = "throttled"
