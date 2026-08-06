"""Controller: workflow lifecycle, retries, review gate, cancellation,
spend protection — the core state-machine behaviors (design doc §2,§8,§9).
"""

import os
import uuid
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test")
os.environ.setdefault("APP_DATABASE_URL", "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret-0123456789abcdef")

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.config import SpendCap
from app.models.enums import JobScheduleStatus, ReviewGateStatus, WorkflowTransitionTrigger
from app.models.pipeline import PipelineRun
from app.models.review_gate import ReviewGate
from app.models.scheduling import JobSchedule
from app.models.workflow import WorkflowDefinition, WorkflowStage, WorkflowTransition
from app.orchestration import controller


async def _make_workspace_item(session):
    ws, user, item = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
        {"id": user, "e": f"{user}@x.com"},
    )
    await session.execute(
        text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"),
        {"id": ws, "u": user},
    )
    await session.execute(
        text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
        {"id": item, "ws": ws},
    )
    return uuid.UUID(ws), uuid.UUID(user), uuid.UUID(item)


async def _two_stage_review_definition(session, workspace_id):
    definition = WorkflowDefinition(
        id=uuid.uuid4(), workspace_id=workspace_id, name="simple", version=1,
    )
    session.add(definition)
    await session.flush()
    session.add_all([
        WorkflowStage(id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
                      stage_key="scripting", ordinal=1, max_attempts=2, backoff_base_seconds=1,
                      backoff_multiplier=2, backoff_max_seconds=5, timeout_seconds=60),
        WorkflowStage(id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
                      stage_key="review", ordinal=2, is_review_gate=True, timeout_seconds=3600),
        WorkflowStage(id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
                      stage_key="published", ordinal=3, is_terminal=True),
    ])
    session.add_all([
        WorkflowTransition(
            id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
            from_stage="scripting", to_stage="review",
            trigger=WorkflowTransitionTrigger.ON_SUCCESS,
        ),
        WorkflowTransition(
            id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
            from_stage="review", to_stage="published",
            trigger=WorkflowTransitionTrigger.ON_REVIEW_APPROVED,
        ),
    ])
    await session.flush()
    return definition


@pytest.mark.asyncio
async def test_start_run_enqueues_first_stage():
    async with AsyncSessionLocal() as session:
        ws, _user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)
        await session.commit()

        result = await session.execute(select(JobSchedule).where(JobSchedule.ref_id == run.id))
        job = result.scalar_one()
        assert job.ref_table == "scripting"
        assert run.current_stage == "scripting"


@pytest.mark.asyncio
async def test_stage_success_advances_to_review_gate_and_pauses():
    async with AsyncSessionLocal() as session:
        ws, _user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)
        await controller.handle_stage_success(session, run=run, stage="scripting")
        await session.commit()

        assert run.status == "paused"
        assert run.pause_reason == "review_gate"
        result = await session.execute(
            select(ReviewGate).where(ReviewGate.pipeline_run_id == run.id)
        )
        gate = result.scalar_one()
        assert gate.status == ReviewGateStatus.AWAITING


@pytest.mark.asyncio
async def test_review_approval_resumes_and_reaches_terminal_stage():
    async with AsyncSessionLocal() as session:
        ws, user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)
        await controller.handle_stage_success(session, run=run, stage="scripting")
        result = await session.execute(
            select(ReviewGate).where(ReviewGate.pipeline_run_id == run.id)
        )
        gate = result.scalar_one()

        await controller.submit_review_decision(session, gate=gate, reviewer_id=user, approved=True)
        await session.commit()

        # The review.approved event was emitted; the relay + registered
        # consumer (app.orchestration.consumers) resolves it to resume.
        from app.orchestration import consumers, relay
        consumers.register_all()
        await relay.poll_and_dispatch(session)
        await session.commit()

        assert run.status == "succeeded"
        assert run.current_stage == "published"


@pytest.mark.asyncio
async def test_stage_failure_retries_then_dead_letters_after_max_attempts():
    async with AsyncSessionLocal() as session:
        ws, _user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        # max_attempts=2 for scripting: first failure retries.
        await controller.handle_stage_failure(
            session, run=run, stage="scripting", attempt_number=1, error_message="timeout",
        )
        await session.commit()
        assert run.status != "failed"

        result = await session.execute(
            select(JobSchedule).where(
                JobSchedule.ref_id == run.id,
                JobSchedule.status == JobScheduleStatus.PENDING,
            )
        )
        retry_job = result.scalars().first()
        assert retry_job is not None

        # Second failure exhausts attempts -> dead-lettered, run failed.
        await controller.handle_stage_failure(
            session, run=run, stage="scripting", attempt_number=2, error_message="timeout",
        )
        await session.commit()
        assert run.status == "failed"

        from app.models.operations import DeadLetterJob
        dlq = await session.execute(select(DeadLetterJob).where(DeadLetterJob.related_id == run.id))
        assert dlq.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_cancel_run_is_idempotent_and_releases_reservations():
    async with AsyncSessionLocal() as session:
        ws, _user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        reservation = await controller.reserve_spend(
            session, run=run, stage="scripting",
            provider="openai", estimated_cost_usd=Decimal("1.00"),
        )
        assert reservation is not None

        await controller.cancel_run(session, run=run)
        await session.commit()
        assert run.status == "cancelled"

        from app.models.enums import ReservationStatus
        await session.refresh(reservation)
        assert reservation.status == ReservationStatus.RELEASED

        # Second cancel is a no-op (idempotent), not an error.
        await controller.cancel_run(session, run=run)
        await session.commit()
        assert run.status == "cancelled"


@pytest.mark.asyncio
async def test_spend_reservation_blocked_over_cap_pauses_run():
    async with AsyncSessionLocal() as session:
        ws, _user, item = await _make_workspace_item(session)
        definition = await _two_stage_review_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        session.add(SpendCap(
            id=uuid.uuid4(), workspace_id=ws, provider="openai",
            daily_cap_usd=Decimal("5.00"), monthly_cap_usd=Decimal("100.00"),
        ))
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        first = await controller.reserve_spend(
            session, run=run, stage="scripting",
            provider="openai", estimated_cost_usd=Decimal("4.00"),
        )
        assert first is not None

        # Different stage — same-stage retry releases the prior reservation
        # (H-4); cap accumulation must be proven across distinct stages.
        second = await controller.reserve_spend(
            session, run=run, stage="voiceover",
            provider="openai", estimated_cost_usd=Decimal("2.00"),
        )
        assert second is None
        assert run.status == "paused"
        assert run.pause_reason == "spend_hold"
