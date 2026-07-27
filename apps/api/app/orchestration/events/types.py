"""Event type name constants — the vocabulary of the bus.

Names are stable; payload shape evolves via event_version + upcasters
(app.orchestration.events.envelope), never by renaming the type in place.
"""

CONTENT_CREATED = "content.created"
PIPELINE_STARTED = "pipeline.started"
PIPELINE_RESUME_REQUESTED = "pipeline.resume_requested"
PIPELINE_CANCEL_REQUESTED = "pipeline.cancel_requested"
PIPELINE_CANCELLED = "pipeline.cancelled"
PIPELINE_FAILED = "pipeline.failed"
PIPELINE_SUCCEEDED = "pipeline.succeeded"

STAGE_ASSIGNED = "stage.assigned"
STAGE_REASSIGNED = "stage.reassigned"
STAGE_COMPLETED = "stage.completed"
STAGE_FAILED = "stage.failed"

REVIEW_REQUESTED = "review.requested"
REVIEW_APPROVED = "review.approved"
REVIEW_REJECTED = "review.rejected"
REVIEW_TIMED_OUT = "review.timed_out"
REVIEW_ESCALATED = "review.escalated"

PUBLISH_REQUESTED = "publish.requested"
PUBLISH_COMPLETED = "publish.completed"

ANALYTICS_RECEIVED = "analytics.received"

SPEND_RESERVED = "spend.reserved"
SPEND_COMMITTED = "spend.committed"
SPEND_RELEASED = "spend.released"
SPEND_BUDGET_EXCEEDED = "spend.budget_exceeded"

# Milestone 4 Workstream 4 — queue-depth back-pressure observability
BACKPRESSURE_ENTERED = "backpressure.entered"
BACKPRESSURE_CLEARED = "backpressure.cleared"

ALL_EVENT_TYPES = {v for k, v in list(vars().items()) if k.isupper() and isinstance(v, str)}
