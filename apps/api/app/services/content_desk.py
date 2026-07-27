"""Private Beta Agency Content Desk — content jobs + review queue.

Orchestration engine already implements the Human Review Gate. This
service is the product adapter: create a draft, land it in review, and
apply decisions via the existing controller/outbox path.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentItem, ContentVersion
from app.models.enums import (
    ContentStage,
    ContentStatus,
    PipelineRunStatus,
    ReviewGateStatus,
    WorkflowTransitionTrigger,
)
from app.models.pipeline import PipelineRun
from app.models.review_gate import ReviewGate
from app.models.workflow import WorkflowDefinition, WorkflowStage, WorkflowTransition
from app.orchestration import consumers, controller, relay

DESK_WORKFLOW_NAME = "agency_content_desk"
DESK_WORKFLOW_VERSION = 1


class ReviewGateNotFoundError(Exception):
    """Review gate missing for the given workspace (not a SQLAlchemy LookupError)."""


@dataclass(frozen=True)
class ContentJobResult:
    content_item_id: uuid.UUID
    pipeline_run_id: uuid.UUID
    review_gate_id: uuid.UUID
    topic: str
    current_stage: str
    run_status: str
    gate_status: str


async def ensure_desk_workflow(
    session: AsyncSession, *, workspace_id: uuid.UUID, created_by: uuid.UUID
) -> WorkflowDefinition:
    """Idempotently provision the Private Beta desk workflow for a workspace."""
    existing = (
        await session.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.workspace_id == workspace_id,
                WorkflowDefinition.name == DESK_WORKFLOW_NAME,
                WorkflowDefinition.version == DESK_WORKFLOW_VERSION,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True
        return existing

    definition = WorkflowDefinition(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        name=DESK_WORKFLOW_NAME,
        version=DESK_WORKFLOW_VERSION,
        is_active=True,
        created_by=created_by,
    )
    session.add(definition)
    await session.flush()
    session.add_all(
        [
            WorkflowStage(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                definition_id=definition.id,
                stage_key=ContentStage.SCRIPTING,
                ordinal=1,
                max_attempts=1,
                timeout_seconds=600,
            ),
            WorkflowStage(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                definition_id=definition.id,
                stage_key=ContentStage.REVIEW,
                ordinal=2,
                is_review_gate=True,
                timeout_seconds=controller.DEFAULT_REVIEW_TIMEOUT_HOURS * 3600,
            ),
            WorkflowStage(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                definition_id=definition.id,
                stage_key=ContentStage.PUBLISHED,
                ordinal=3,
                is_terminal=True,
                timeout_seconds=60,
            ),
        ]
    )
    session.add(
        WorkflowTransition(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            definition_id=definition.id,
            from_stage=ContentStage.SCRIPTING,
            to_stage=ContentStage.REVIEW,
            trigger=WorkflowTransitionTrigger.ON_SUCCESS,
            priority=100,
        )
    )
    session.add(
        WorkflowTransition(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            definition_id=definition.id,
            from_stage=ContentStage.REVIEW,
            to_stage=ContentStage.PUBLISHED,
            trigger=WorkflowTransitionTrigger.ON_REVIEW_APPROVED,
            priority=100,
        )
    )
    await session.flush()
    return definition


async def create_content_job(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    topic: str,
    script_body: str,
    script_hook: str | None = None,
    script_cta: str | None = None,
    target_length_seconds: int | None = None,
    idempotency_key: str | None = None,
) -> ContentJobResult:
    """Create draft content and advance it into the mandatory Review Gate.

    Private Beta generation is intentionally a stub: the caller-supplied
    script is treated as the scripting-stage output so the Gate is reachable
    without a live AI provider. The Gate itself is never skipped.
    """
    if idempotency_key is not None:
        existing_run = (
            await session.execute(
                select(PipelineRun).where(
                    PipelineRun.workspace_id == workspace_id,
                    PipelineRun.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing_run is not None:
            gate = (
                await session.execute(
                    select(ReviewGate).where(ReviewGate.pipeline_run_id == existing_run.id)
                )
            ).scalar_one_or_none()
            item = await session.get(ContentItem, existing_run.content_item_id)
            if gate is None or item is None:
                raise ValueError("idempotent content job is missing review gate or content item")
            return ContentJobResult(
                content_item_id=item.id,
                pipeline_run_id=existing_run.id,
                review_gate_id=gate.id,
                topic=item.topic,
                current_stage=str(
                    existing_run.current_stage.value
                    if hasattr(existing_run.current_stage, "value")
                    else existing_run.current_stage
                ),
                run_status=str(
                    existing_run.status.value
                    if hasattr(existing_run.status, "value")
                    else existing_run.status
                ),
                gate_status=str(
                    gate.status.value if hasattr(gate.status, "value") else gate.status
                ),
            )

    definition = await ensure_desk_workflow(session, workspace_id=workspace_id, created_by=actor_id)

    item = ContentItem(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        topic=topic,
        target_length_seconds=target_length_seconds,
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(item)
    await session.flush()

    version = ContentVersion(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_item_id=item.id,
        script_hook=script_hook,
        script_body=script_body,
        script_cta=script_cta,
        prompt_used="private_beta_manual_draft",
        generated_by="private_beta_draft",
        created_by=actor_id,
    )
    session.add(version)
    await session.flush()
    item.current_version_id = version.id

    run = PipelineRun(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_item_id=item.id,
        idempotency_key=idempotency_key,
        current_stage=ContentStage.SCRIPTING,
        status=PipelineRunStatus.RUNNING,
    )
    session.add(run)
    await session.flush()
    item.current_pipeline_run_id = run.id

    await controller.start_run(session, run=run, definition=definition)
    await controller.handle_stage_success(
        session,
        run=run,
        stage=ContentStage.SCRIPTING.value,
        result_context={"draft_version_id": str(version.id)},
    )

    gate = (
        await session.execute(select(ReviewGate).where(ReviewGate.pipeline_run_id == run.id))
    ).scalar_one_or_none()
    if gate is None or gate.status != ReviewGateStatus.AWAITING:
        raise RuntimeError("content job failed to enter Human Review Gate")

    item.current_stage = ContentStage.REVIEW
    await session.flush()

    return ContentJobResult(
        content_item_id=item.id,
        pipeline_run_id=run.id,
        review_gate_id=gate.id,
        topic=item.topic,
        current_stage=ContentStage.REVIEW.value,
        run_status=str(run.status.value if hasattr(run.status, "value") else run.status),
        gate_status=ReviewGateStatus.AWAITING.value,
    )


async def list_review_gates(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    status_filter: str | None = None,
) -> list[dict]:
    stmt = (
        select(ReviewGate, PipelineRun, ContentItem, ContentVersion)
        .join(PipelineRun, PipelineRun.id == ReviewGate.pipeline_run_id)
        .join(ContentItem, ContentItem.id == PipelineRun.content_item_id)
        .outerjoin(ContentVersion, ContentVersion.id == ContentItem.current_version_id)
        .where(ReviewGate.workspace_id == workspace_id)
        .order_by(ReviewGate.requested_at.desc())
    )
    if status_filter is not None:
        stmt = stmt.where(ReviewGate.status == ReviewGateStatus(status_filter))
    rows = (await session.execute(stmt)).all()
    out: list[dict] = []
    for gate, run, item, version in rows:
        out.append(_gate_row(gate, run, item, version))
    return out


async def get_review_gate(
    session: AsyncSession, *, workspace_id: uuid.UUID, gate_id: uuid.UUID
) -> dict | None:
    row = (
        await session.execute(
            select(ReviewGate, PipelineRun, ContentItem, ContentVersion)
            .join(PipelineRun, PipelineRun.id == ReviewGate.pipeline_run_id)
            .join(ContentItem, ContentItem.id == PipelineRun.content_item_id)
            .outerjoin(ContentVersion, ContentVersion.id == ContentItem.current_version_id)
            .where(
                ReviewGate.workspace_id == workspace_id,
                ReviewGate.id == gate_id,
            )
        )
    ).first()
    if row is None:
        return None
    gate, run, item, version = row
    return _gate_row(gate, run, item, version)


async def decide_review_gate(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    gate_id: uuid.UUID,
    reviewer_id: uuid.UUID,
    approved: bool,
    notes: str | None = None,
) -> dict:
    gate = (
        await session.execute(
            select(ReviewGate).where(
                ReviewGate.workspace_id == workspace_id,
                ReviewGate.id == gate_id,
            )
        )
    ).scalar_one_or_none()
    if gate is None:
        raise ReviewGateNotFoundError("review gate not found")
    if gate.status != ReviewGateStatus.AWAITING:
        raise ValueError("review gate is not awaiting a decision")

    await controller.submit_review_decision(
        session,
        gate=gate,
        reviewer_id=reviewer_id,
        approved=approved,
        notes=notes,
    )
    # Ensure bus consumers are registered, then deliver in-process so the
    # HTTP caller sees the advanced run without waiting for the background tick.
    consumers.register_all()
    await relay.poll_and_dispatch(session)
    await session.flush()

    detail = await get_review_gate(session, workspace_id=workspace_id, gate_id=gate_id)
    if detail is None:
        raise RuntimeError("review gate disappeared after decision")
    return detail


def _gate_row(
    gate: ReviewGate,
    run: PipelineRun,
    item: ContentItem,
    version: ContentVersion | None,
) -> dict:
    stage = gate.stage.value if hasattr(gate.stage, "value") else str(gate.stage)
    status = gate.status.value if hasattr(gate.status, "value") else str(gate.status)
    run_status = run.status.value if hasattr(run.status, "value") else str(run.status)
    return {
        "id": gate.id,
        "workspace_id": gate.workspace_id,
        "pipeline_run_id": gate.pipeline_run_id,
        "content_item_id": item.id,
        "topic": item.topic,
        "stage": stage,
        "status": status,
        "requested_at": gate.requested_at,
        "timeout_at": gate.timeout_at,
        "decided_at": gate.decided_at,
        "decided_by": gate.decided_by,
        "script_hook": version.script_hook if version else None,
        "script_body": version.script_body if version else None,
        "script_cta": version.script_cta if version else None,
        "run_status": run_status,
    }
