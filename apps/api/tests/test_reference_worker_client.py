"""End-to-end: dispatch a stage, have the reference worker client claim,
heartbeat, execute (canned success), and submit — proving the whole
worker-side contract without any real generation logic.
"""

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test")
os.environ.setdefault("APP_DATABASE_URL", "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")

# apps/worker isn't installed as a dependency of apps/api; reach it via a
# relative path so this integration test can import the reference client
# without requiring a separate package install step in CI.
sys.path.append(str(Path(__file__).resolve().parents[3] / "worker"))

import pytest
from sqlalchemy import select, text

from app.db.session import AsyncSessionLocal
from app.models.enums import StageAssignmentStatus, WorkflowTransitionTrigger
from app.models.pipeline import PipelineRun
from app.models.workflow import WorkflowDefinition, WorkflowStage, WorkflowTransition
from app.orchestration import controller, dispatcher

from worker.client import ReferenceWorkerClient  # noqa: E402


async def _make_workspace_item(session):
    ws, user, item = str(uuid.uuid4()), str(uuid.uuid4()), str(uuid.uuid4())
    await session.execute(text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"), {"id": user, "e": f"{user}@x.com"})
    await session.execute(text("INSERT INTO workspaces (id, name, created_by) VALUES (:id, 'w', :u)"), {"id": ws, "u": user})
    await session.execute(text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"), {"id": item, "ws": ws})
    return uuid.UUID(ws), uuid.UUID(item)


@pytest.mark.asyncio
async def test_reference_worker_client_completes_a_stage_end_to_end():
    async with AsyncSessionLocal() as session:
        ws, item = await _make_workspace_item(session)
        definition = WorkflowDefinition(id=uuid.uuid4(), workspace_id=ws, name="one-stage", version=1)
        session.add(definition)
        await session.flush()
        session.add(WorkflowStage(id=uuid.uuid4(), workspace_id=ws, definition_id=definition.id,
                                   stage_key="scripting", ordinal=1, is_terminal=True))
        await session.flush()

        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        assignment = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage="scripting",
            attempt_number=1, correlation_id=run.correlation_id, trace_id=run.trace_id,
        )
        await session.commit()

    client = ReferenceWorkerClient(name="ref-1", supported_stages=["scripting"])
    async with AsyncSessionLocal() as session:
        await client.register(session)
        await session.commit()

    async with AsyncSessionLocal() as session:
        claimed = await client.claim_next(session)
        assert claimed is not None
        assert claimed.status == StageAssignmentStatus.ACKNOWLEDGED
        await client.heartbeat(session)
        await client.run_one(session, claimed)
        await session.commit()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PipelineRun).where(PipelineRun.id == run.id))
        refreshed = result.scalar_one()
        assert refreshed.status == "succeeded"
