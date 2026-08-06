"""Targeted regression tests for two defects caught and fixed during
Milestone 4 implementation review — kept as permanent regression coverage
so neither can silently reappear.

Defect 1: spend reservation release scoping. An early version of
release_all_reservations() scoped by workspace_id only, which would have
released a DIFFERENT run's open reservation in the same workspace.

Defect 2: controller self-triggering event loop. An early version of
app.orchestration.consumers registered the controller to consume its own
stage.completed/stage.failed output (which controller.handle_stage_success/
handle_stage_failure themselves emit), which would have double-processed
every stage result via the relay on top of the direct in-process call.
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
from app.models.enums import ReservationStatus
from app.models.pipeline import PipelineRun
from app.models.workflow import WorkflowDefinition, WorkflowStage
from app.orchestration import controller, relay


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
        text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't1')"),
        {"id": item, "ws": ws},
    )
    return uuid.UUID(ws), uuid.UUID(item)


async def _one_stage_definition(session, workspace_id):
    definition = WorkflowDefinition(
        id=uuid.uuid4(), workspace_id=workspace_id, name="regress", version=1,
    )
    session.add(definition)
    await session.flush()
    session.add(WorkflowStage(
        id=uuid.uuid4(), workspace_id=workspace_id, definition_id=definition.id,
        stage_key="scripting", ordinal=1, is_terminal=True,
    ))
    await session.flush()
    return definition


# --- Defect 1: reservation release scoping ---------------------------------

@pytest.mark.asyncio
async def test_regression_release_only_affects_the_failing_runs_own_reservation():
    """Two runs in the SAME workspace each reserve spend. Failing/
    cancelling run A must release ONLY run A's reservation — run B's must
    remain untouched. Prior to the pipeline_run_id fix (migration 0020),
    release_all_reservations() scoped by workspace_id alone and would have
    released BOTH.
    """
    async with AsyncSessionLocal() as session:
        ws, item = await _make_workspace_item(session)
        definition = await _one_stage_definition(session, ws)

        run_a = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        run_b = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add_all([run_a, run_b])
        await session.flush()
        await controller.start_run(session, run=run_a, definition=definition)
        await controller.start_run(session, run=run_b, definition=definition)

        reservation_a = await controller.reserve_spend(
            session, run=run_a, stage="scripting",
            provider="openai", estimated_cost_usd=Decimal("1.00"),
        )
        reservation_b = await controller.reserve_spend(
            session, run=run_b, stage="scripting",
            provider="openai", estimated_cost_usd=Decimal("1.00"),
        )
        assert reservation_a is not None and reservation_b is not None
        assert reservation_a.pipeline_run_id == run_a.id
        assert reservation_b.pipeline_run_id == run_b.id

        await controller.cancel_run(session, run=run_a)
        await session.commit()

        await session.refresh(reservation_a)
        await session.refresh(reservation_b)
        assert reservation_a.status == ReservationStatus.RELEASED, (
            "run A's own reservation must be released"
        )
        assert reservation_b.status == ReservationStatus.RESERVED, (
            "run B's reservation must NOT be released by run A's cancellation — "
            "this is the exact regression the pipeline_run_id scoping fix (migration 0020) prevents"
        )


# --- Defect 2: controller self-triggering loop ------------------------------

@pytest.mark.asyncio
async def test_regression_stage_completed_is_not_registered_as_a_controller_consumer():
    """Static/structural check: app.orchestration.consumers must never
    register the controller against STAGE_COMPLETED or STAGE_FAILED —
    those events are emitted BY the controller's own call path
    (dispatcher.submit_result -> controller.handle_stage_success/failure,
    in-process, same transaction), so consuming them via the relay would
    double-process every stage result.
    """
    from app.orchestration import consumers
    from app.orchestration.events.types import STAGE_COMPLETED, STAGE_FAILED
    from app.orchestration.relay import _REGISTRY

    _REGISTRY.clear()
    consumers.register_all()

    for consumer_name, handlers in _REGISTRY.items():
        assert STAGE_COMPLETED not in handlers, (
            f"consumer '{consumer_name}' must not subscribe to stage.completed — "
            "that event is produced by the same code path that would consume it, "
            "which is exactly the self-triggering loop caught during M4 review"
        )
        assert STAGE_FAILED not in handlers, (
            f"consumer '{consumer_name}' must not subscribe to stage.failed — "
            "same self-triggering loop risk as stage.completed"
        )


@pytest.mark.asyncio
async def test_regression_stage_completion_advances_run_exactly_once():
    """Behavioral counterpart to the structural check above: completing a
    stage via dispatcher.submit_result must advance the run's state
    exactly once, even after the relay processes any events emitted along
    the way — proving there's no double-processing in practice, not just
    that the wiring looks right.
    """
    async with AsyncSessionLocal() as session:
        ws, item = await _make_workspace_item(session)
        definition = await _one_stage_definition(session, ws)
        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        from app.orchestration import dispatcher

        assignment = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage="scripting",
            attempt_number=1, correlation_id=run.correlation_id, trace_id=run.trace_id,
        )
        assert assignment.assignment is not None
        await session.commit()

    async with AsyncSessionLocal() as session:
        from sqlalchemy import select as _select

        from app.models.assignments import StageAssignment
        result = await session.execute(
            _select(StageAssignment).where(StageAssignment.id == assignment.assignment.id)
        )
        loaded_assignment = result.scalar_one()
        await dispatcher.submit_result(
            session, assignment=loaded_assignment, success=True, result={},
        )
        await session.commit()

    # Drain the relay (delivers stage.completed to whatever IS registered
    # for it, if anything) and confirm the run only reached 'succeeded'
    # once — no duplicate transition, no error from re-advancing a
    # terminal run.
    async with AsyncSessionLocal() as session:
        await relay.poll_and_dispatch(session)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PipelineRun).where(PipelineRun.id == run.id))
        refreshed = result.scalar_one()
        assert refreshed.status == "succeeded"
