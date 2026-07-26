"""End-to-end: dispatch a stage, have the reference worker client claim,
heartbeat, execute (canned success), and submit — proving the whole
worker-side contract without any real generation logic.
"""

import os
import sys
import uuid
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/content_orchestrator_test")
os.environ.setdefault("APP_DATABASE_URL", "postgresql://app_runtime:app_runtime@localhost:5432/content_orchestrator_test")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret")

# apps/worker isn't installed as a dependency of apps/api; reach it via a
# relative path so this integration test can import the reference client
# without requiring a separate package install step in CI.
sys.path.append(str(Path(__file__).resolve().parents[2] / "worker"))

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy import select, text
from worker.client import ReferenceWorkerClient  # noqa: E402

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.enums import StageAssignmentStatus
from app.models.pipeline import PipelineRun
from app.models.workflow import WorkflowDefinition, WorkflowStage
from app.orchestration import controller, dispatcher
from tests.conftest import make_token


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
        text(
            "INSERT INTO workspace_memberships (workspace_id, user_id, role) "
            "VALUES (:ws, :u, 'admin')"
        ),
        {"ws": ws, "u": user},
    )
    await session.execute(
        text("INSERT INTO content_items (id, workspace_id, topic) VALUES (:id, :ws, 't')"),
        {"id": item, "ws": ws},
    )
    return uuid.UUID(ws), uuid.UUID(item), user


@pytest.mark.asyncio
async def test_reference_worker_client_completes_a_stage_end_to_end():
    async with AsyncSessionLocal() as session:
        # Park all pre-existing online/busy workers so dispatch_stage sees no
        # eligible worker and creates the assignment as PENDING (not DISPATCHED).
        # claim_next only polls PENDING; a DISPATCHED assignment would never be
        # found by the pull-mode client.
        await session.execute(
            text(
                "UPDATE worker_registry SET status = 'offline'::worker_status "
                "WHERE status IN ('online'::worker_status, 'busy'::worker_status)"
            )
        )

        ws, item, admin_user = await _make_workspace_item(session)
        definition = WorkflowDefinition(
            id=uuid.uuid4(), workspace_id=ws, name="one-stage", version=1,
        )
        session.add(definition)
        await session.flush()
        session.add(WorkflowStage(id=uuid.uuid4(), workspace_id=ws, definition_id=definition.id,
                                   stage_key="scripting", ordinal=1, is_terminal=True))
        await session.flush()

        run = PipelineRun(id=uuid.uuid4(), workspace_id=ws, content_item_id=item)
        session.add(run)
        await session.flush()
        await controller.start_run(session, run=run, definition=definition)

        dispatched = await dispatcher.dispatch_stage(
            session, workspace_id=ws, pipeline_run_id=run.id, stage="scripting",
            attempt_number=1, correlation_id=run.correlation_id, trace_id=run.trace_id,
        )
        await session.commit()
        run_id = run.id
        assignment_id = dispatched.id  # capture before session closes

    # WS1: lifecycle over HTTP — provision (admin JWT) then register with
    # the per-worker credential. Claim/submit still ride the DB session.
    http = httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    admin_headers = {"Authorization": f"Bearer {make_token(user_id=admin_user)}"}
    provision = await http.post(
        f"/workspaces/{ws}/workers",
        headers=admin_headers,
        json={"name": "ref-1", "supported_stages": ["scripting"], "max_concurrency": 1},
    )
    assert provision.status_code == 201, provision.text
    provisioned = provision.json()

    client = ReferenceWorkerClient(
        name="ref-1", supported_stages=["scripting"], http=http,
        credential=provisioned["worker_secret"], worker_id=provisioned["worker_id"],
    )
    await client.register()

    # Retire stale PENDING assignments from prior test runs so claim_next
    # picks up THIS test's assignment rather than an older one whose
    # pipeline_run may have definition_id=None.
    async with AsyncSessionLocal() as session:
        await session.execute(
            text(
                "UPDATE stage_assignments SET status = 'failed' "
                "WHERE status = 'pending' AND id != :id"
            ),
            {"id": str(assignment_id)},
        )
        await session.commit()

    async with AsyncSessionLocal() as session:
        claimed = await client.claim_next(session)
        assert claimed is not None
        assert claimed.status == StageAssignmentStatus.ACKNOWLEDGED
        await client.heartbeat()
        await client.run_one(session, claimed)
        await session.commit()

    await http.aclose()

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PipelineRun).where(PipelineRun.id == run_id))
        refreshed = result.scalar_one()
        assert refreshed.status == "succeeded"
