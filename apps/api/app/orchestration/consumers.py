"""Wires event-bus-mediated reactions. Imported once at process start so
registration happens exactly once.

IMPORTANT: stage.completed and stage.failed are NOT consumed here. They
are emitted by app.orchestration.dispatcher.submit_result, which already
calls controller.handle_stage_success/handle_stage_failure directly, in
the same transaction, as the actual mechanism for advancing the run —
those two functions are what PRODUCE stage.completed/stage.failed for
other observers (metrics, future notification consumers). Also wiring
the controller to consume its own output here would double-process every
stage result. review.approved/review.rejected genuinely need bus-mediated
decoupling because they're produced by a separate actor (a reviewer,
via the review_decisions write path) that has no direct call into the
controller.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.events import OutboxEvent
from app.models.review_gate import ReviewGate
from app.orchestration import controller
from app.orchestration.relay import register_consumer


async def _on_review_approved(session: AsyncSession, event: OutboxEvent) -> None:
    gate_id = uuid.UUID(event.payload["review_gate_id"])
    gate = await session.get(ReviewGate, gate_id)
    if gate is not None:
        await controller.resume_from_review(session, gate=gate, approved=True)


async def _on_review_rejected(session: AsyncSession, event: OutboxEvent) -> None:
    gate_id = uuid.UUID(event.payload["review_gate_id"])
    gate = await session.get(ReviewGate, gate_id)
    if gate is not None:
        await controller.resume_from_review(session, gate=gate, approved=False)


def register_all() -> None:
    from app.orchestration.events.types import REVIEW_APPROVED, REVIEW_REJECTED

    register_consumer("pipeline-controller", REVIEW_APPROVED, _on_review_approved)
    register_consumer("pipeline-controller", REVIEW_REJECTED, _on_review_rejected)
