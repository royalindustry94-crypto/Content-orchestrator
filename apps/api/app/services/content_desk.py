from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.content import ContentItem, ContentVersion
from app.models.enums import (
    ContentStage,
    JobScheduleStatus,
    JobType,
    PipelineRunStatus,
    ReviewGateStatus,
)
from app.models.review_gate import ReviewGate
from app.models.scheduling import JobSchedule
from app.models.workflow import PipelineRun, WorkflowDefinition
from app.orchestration import controller


class SpendBudgetExceededError(Exception):
    pass


DRAFT_DESK_PROVIDER = "draft_desk"


async def ensure_desk_workflow(
    session: AsyncSession, *, workspace_id: uuid.UUID, created_by: uuid.UUID
) -> WorkflowDefinition:
    existing = (
        await session.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.workspace_id == workspace_id,
                WorkflowDefinition.name == "agency_content_desk",
                WorkflowDefinition.version == 1,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    definition = await controller.create_workflow_definition(
        session,
        workspace_id=workspace_id,
        name="agency_content_desk",
        version=1,
        stages=[
            {
                "stage": ContentStage.SCRIPTING.value,
                "sequence": 1,
                "requires_human_review": True,
                "retry_max_attempts": 3,
            },
        ],
        created_by=created_by,
    )
    return definition


async def open_review_gate(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    definition: WorkflowDefinition,
    item: ContentItem,
    version: ContentVersion,
    provider: str,
    idempotency_key: str | None = None,
) -> tuple[PipelineRun, ReviewGate]:
    """Run a content version through scripting and into the Human Review Gate.

    Every path that puts content in front of a reviewer goes through here, so
    there is one implementation of the gate and no way to reach ``published``
    without passing it.
    """
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
    estimate = Decimal(str(get_settings().default_stage_estimate_usd))
    reservation = await controller.reserve_spend(
        session,
        run=run,
        stage=ContentStage.SCRIPTING.value,
        provider=provider,
        estimated_cost_usd=estimate,
    )
    if reservation is None:
        raise SpendBudgetExceededError(
            "workspace spend cap exceeded; pipeline run paused on spend_hold"
        )

    # Simulation is deliberately zero-cost, but it still exercises the same
    # fail-closed reservation path so budget controls remain testable. The
    # reservation is reconciled to zero actual provider spend on success.
    actual_cost = Decimal("0.00") if provider == "simulation" else estimate
    await controller.handle_stage_success(
        session,
        run=run,
        stage=ContentStage.SCRIPTING.value,
        result_context={
            "draft_version_id": str(version.id),
            "estimated_cost_usd": str(estimate),
            "actual_cost_usd": str(actual_cost),
            "provider": provider,
        },
    )
    await controller.commit_spend(
        session,
        run=run,
        reservation=reservation,
        actual_cost_usd=actual_cost,
    )

    orphan_jobs = (
        await session.execute(
            select(JobSchedule).where(
                JobSchedule.ref_id == run.id,
                JobSchedule.job_type.in_([JobType.STAGE, JobType.RETRY]),
                JobSchedule.ref_table == ContentStage.SCRIPTING.value,
                JobSchedule.status.in_(
                    [JobScheduleStatus.PENDING, JobScheduleStatus.LEASED]
                ),
            )
        )
    ).scalars().all()
    for job in orphan_jobs:
        job.status = JobScheduleStatus.CANCELLED
        job.lease_owner = None
        job.lease_expires_at = None

    gate = (
        await session.execute(select(ReviewGate).where(ReviewGate.pipeline_run_id == run.id))
    ).scalar_one_or_none()
    if gate is None or gate.status != ReviewGateStatus.AWAITING:
        raise RuntimeError("content failed to enter Human Review Gate")

    item.current_stage = ContentStage.REVIEW
    await session.flush()
    return run, gate


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
):
    """Create draft content and advance it into the mandatory Review Gate."""
    definition = await ensure_desk_workflow(
        session, workspace_id=workspace_id, created_by=actor_id
    )
    item = ContentItem(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title=topic,
        current_stage=ContentStage.SCRIPTING,
        created_by=actor_id,
    )
    session.add(item)
    await session.flush()

    version = ContentVersion(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_item_id=item.id,
        version_number=1,
        script_body=script_body,
        script_hook=script_hook,
        script_cta=script_cta,
        target_length_seconds=target_length_seconds,
        created_by=actor_id,
    )
    session.add(version)
    await session.flush()
    item.current_version_id = version.id

    run, gate = await open_review_gate(
        session,
        workspace_id=workspace_id,
        definition=definition,
        item=item,
        version=version,
        provider=DRAFT_DESK_PROVIDER,
        idempotency_key=idempotency_key,
    )

    from app.schemas.content_desk import ContentJobResult

    return ContentJobResult(
        content_item_id=item.id,
        pipeline_run_id=run.id,
        review_gate_id=gate.id,
        status=gate.status.value,
    )
