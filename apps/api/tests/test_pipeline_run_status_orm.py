"""P0-1: PipelineRunStatus must round-trip every DB enum value via ORM."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.enums import PipelineRunStatus
from app.models.pipeline import PipelineRun
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.orchestration import controller


async def _seed_workspace(session) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    user_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    await session.execute(
        text(
            "INSERT INTO profiles (id, email) VALUES (:id, :email) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    ws = Workspace(id=uuid.uuid4(), name=f"orm-{user_id}", created_by=user_id)
    session.add(ws)
    await session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=ws.id, user_id=user_id, role=WorkspaceRole.ADMIN
        )
    )
    from app.models.content import ContentItem
    from app.models.enums import ContentStage, ContentStatus

    item = ContentItem(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        topic="ORM enum check",
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()
    return ws.id, user_id, item.id


@pytest.mark.asyncio
async def test_db_pipeline_run_status_values_match_python_enum():
    async with AsyncSessionLocal() as session:
        rows = (
            await session.execute(text("SELECT unnest(enum_range(NULL::pipeline_run_status))"))
        ).scalars().all()
    db_values = {str(v) for v in rows}
    py_values = {e.value for e in PipelineRunStatus}
    assert db_values == py_values


@pytest.mark.asyncio
async def test_orm_reload_after_human_review_pause():
    """Regression: paused runs must reload without LookupError."""
    run_id = None
    async with AsyncSessionLocal() as session:
        ws_id, user_id, item_id = await _seed_workspace(session)
        from app.models.enums import ContentStage, WorkflowTransitionTrigger
        from app.models.workflow import WorkflowDefinition, WorkflowStage, WorkflowTransition

        definition = WorkflowDefinition(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            name="orm_pause_check",
            version=1,
            is_active=True,
            created_by=user_id,
        )
        session.add(definition)
        await session.flush()
        session.add_all(
            [
                WorkflowStage(
                    id=uuid.uuid4(),
                    workspace_id=ws_id,
                    definition_id=definition.id,
                    stage_key=ContentStage.SCRIPTING,
                    ordinal=1,
                    max_attempts=1,
                    timeout_seconds=60,
                ),
                WorkflowStage(
                    id=uuid.uuid4(),
                    workspace_id=ws_id,
                    definition_id=definition.id,
                    stage_key=ContentStage.REVIEW,
                    ordinal=2,
                    is_review_gate=True,
                    timeout_seconds=3600,
                ),
                WorkflowStage(
                    id=uuid.uuid4(),
                    workspace_id=ws_id,
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
                workspace_id=ws_id,
                definition_id=definition.id,
                from_stage=ContentStage.SCRIPTING,
                to_stage=ContentStage.REVIEW,
                trigger=WorkflowTransitionTrigger.ON_SUCCESS,
                priority=100,
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws_id,
            content_item_id=item_id,
            current_stage=ContentStage.SCRIPTING,
            status=PipelineRunStatus.RUNNING,
        )
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)
        await controller.handle_stage_success(session, run=run, stage="scripting")
        assert run.status == PipelineRunStatus.PAUSED
        run_id = run.id
        await session.commit()

    async with AsyncSessionLocal() as session:
        reloaded = await session.get(PipelineRun, run_id)
        assert reloaded is not None
        assert reloaded.status == PipelineRunStatus.PAUSED
        assert reloaded.pause_reason == "review_gate"


@pytest.mark.asyncio
async def test_all_pipeline_status_values_persist_and_reload():
    async with AsyncSessionLocal() as session:
        ws_id, user_id, item_id = await _seed_workspace(session)
        ids: dict[str, uuid.UUID] = {}
        for status in PipelineRunStatus:
            run = PipelineRun(
                id=uuid.uuid4(),
                workspace_id=ws_id,
                content_item_id=item_id,
                status=status,
            )
            session.add(run)
            ids[status.value] = run.id
        await session.commit()

    async with AsyncSessionLocal() as session:
        for value, run_id in ids.items():
            row = await session.get(PipelineRun, run_id)
            assert row is not None
            assert row.status == PipelineRunStatus(value)
