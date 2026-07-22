"""Event envelope construction and versioning (upcasting).

The envelope shape is fixed (see docs/milestone-4-orchestration-design.md
§3.2). This module is the single place that builds it and the single
place payload upcasters live, so producers and consumers never hand-roll
either.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class EventEnvelope:
    event_type: str
    workspace_id: uuid.UUID
    aggregate_type: str
    aggregate_id: uuid.UUID
    correlation_id: uuid.UUID
    payload: dict[str, Any]
    produced_by: str
    causation_id: uuid.UUID | None = None
    trace_id: str | None = None
    span_id: str | None = None
    event_version: int = 1
    event_id: uuid.UUID = field(default_factory=uuid.uuid4)
    occurred_at: datetime = field(default_factory=_utcnow)


def new_trace_id() -> str:
    """32-hex-char id, W3C-traceparent-compatible, for a brand-new trace
    (a workflow execution that has no parent trace to join)."""
    return uuid.uuid4().hex


def new_span_id() -> str:
    """16-hex-char id for one hop within a trace."""
    return uuid.uuid4().hex[:16]


def child_span(trace_id: str | None) -> tuple[str, str]:
    """Continue an existing trace with a new span, or start a fresh trace
    if none exists yet (e.g. the very first event of a pipeline run).
    """
    return (trace_id or new_trace_id()), new_span_id()


# --- payload upcasters -----------------------------------------------
# Registry of (event_type, from_version) -> function(payload) -> payload
# at from_version+1. Applied repeatedly until the payload reaches the
# consumer's max_event_version. Empty until a real payload change needs
# one — not stubbed with a fake example that would need removing later.
_UPCASTERS: dict[tuple[str, int], Callable[[dict], dict]] = {}


def register_upcaster(event_type: str, from_version: int, fn: Callable[[dict], dict]) -> None:
    _UPCASTERS[(event_type, from_version)] = fn


def upcast(event_type: str, version: int, payload: dict, target_version: int) -> dict:
    """Apply registered upcasters in sequence until `target_version` is
    reached. A payload with no registered upcaster path is returned as-is
    (the common case while only version 1 exists).
    """
    current_version, current_payload = version, payload
    while current_version < target_version:
        fn = _UPCASTERS.get((event_type, current_version))
        if fn is None:
            break
        current_payload = fn(current_payload)
        current_version += 1
    return current_payload
