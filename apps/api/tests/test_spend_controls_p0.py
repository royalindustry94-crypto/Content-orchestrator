"""P0-4: monthly cap, spend seed, spend API, automatic pause."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from app.models.content import ContentItem
from app.models.enums import ContentStage, ContentStatus, PipelineRunStatus
from app.models.pipeline import PipelineRun
from app.models.spend import SpendLog
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.orchestration import controller
from app.services.spend import ensure_default_spend_cap


async def _user_workspace(session):
    user_id = uuid.uuid4()
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    await session.execute(
        text(
            "INSERT INTO profiles (id, email) VALUES (:id, :email) ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(user_id), "email": f"{user_id}@example.com"},
    )
    ws = Workspace(id=uuid.uuid4(), name=f"spend-{user_id}", created_by=user_id)
    session.add(ws)
    await session.flush()
    session.add(
        WorkspaceMembership(
            workspace_id=ws.id, user_id=user_id, role=WorkspaceRole.ADMIN
        )
    )
    await ensure_default_spend_cap(session, workspace_id=ws.id, actor_id=user_id)
    item = ContentItem(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        topic="spend topic",
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()
    return ws, user_id, item


@pytest.mark.asyncio
async def test_workspace_create_seeds_spend_cap(client, new_user):
    _user_id, _token, headers = new_user
    create = await client.post("/workspaces", headers=headers, json={"name": "Seed Cap Co"})
    assert create.status_code == 201
    ws_id = create.json()["id"]
    spend = await client.get(f"/workspaces/{ws_id}/spend", headers=headers)
    assert spend.status_code == 200
    body = spend.json()
    assert body["daily_cap_usd"] == 50.0
    assert body["monthly_cap_usd"] == 1000.0


@pytest.mark.asyncio
async def test_spend_api_update_caps(client, new_user):
    _user_id, _token, headers = new_user
    create = await client.post("/workspaces", headers=headers, json={"name": "Cap Update"})
    ws_id = create.json()["id"]
    patched = await client.patch(
        f"/workspaces/{ws_id}/spend",
        headers=headers,
        json={"daily_cap_usd": 5.0, "monthly_cap_usd": 20.0},
    )
    assert patched.status_code == 200
    assert patched.json()["daily_cap_usd"] == 5.0
    assert patched.json()["monthly_cap_usd"] == 20.0


@pytest.mark.asyncio
async def test_monthly_cap_pauses_run():
    async with AsyncSessionLocal() as session:
        ws, user_id, item = await _user_workspace(session)
        cap = (
            await session.execute(
                text("SELECT id FROM spend_caps WHERE workspace_id = :ws"),
                {"ws": str(ws.id)},
            )
        ).scalar_one()
        # Force a tiny monthly cap; leave daily high.
        await session.execute(
            text(
                "UPDATE spend_caps SET daily_cap_usd = 1000, monthly_cap_usd = 1 "
                "WHERE id = :id"
            ),
            {"id": str(cap)},
        )
        session.add(
            SpendLog(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                provider="draft_desk",
                stage=ContentStage.SCRIPTING,
                cost_usd=Decimal("0.99"),
                occurred_at=datetime.now(UTC),
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            content_item_id=item.id,
            status=PipelineRunStatus.RUNNING,
            current_stage=ContentStage.SCRIPTING,
            correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()
        reservation = await controller.reserve_spend(
            session,
            run=run,
            stage="scripting",
            provider="draft_desk",
            estimated_cost_usd=Decimal("0.05"),
        )
        assert reservation is None
        assert run.status == PipelineRunStatus.PAUSED
        assert run.pause_reason == "spend_hold"
        await session.commit()


@pytest.mark.asyncio
async def test_workspace_cap_counts_all_providers():
    """Regression: workspace-wide monthly cap must not be bypassed by
    spending on provider A then reserving against provider B.
    """
    async with AsyncSessionLocal() as session:
        ws, _user_id, item = await _user_workspace(session)
        await session.execute(
            text(
                "UPDATE spend_caps SET daily_cap_usd = 1000, monthly_cap_usd = 1 "
                "WHERE workspace_id = :ws"
            ),
            {"ws": str(ws.id)},
        )
        session.add(
            SpendLog(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                provider="openai",
                stage=ContentStage.SCRIPTING,
                cost_usd=Decimal("0.99"),
                occurred_at=datetime.now(UTC),
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            content_item_id=item.id,
            status=PipelineRunStatus.RUNNING,
            correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()
        reservation = await controller.reserve_spend(
            session,
            run=run,
            stage="scripting",
            provider="draft_desk",
            estimated_cost_usd=Decimal("0.05"),
        )
        assert reservation is None
        assert run.status == PipelineRunStatus.PAUSED
        assert run.pause_reason == "spend_hold"
        await session.commit()


@pytest.mark.asyncio
async def test_content_job_blocked_when_monthly_cap_exceeded(client, new_user):
    _user_id, _token, headers = new_user
    create = await client.post("/workspaces", headers=headers, json={"name": "Tight Cap"})
    ws_id = create.json()["id"]
    # spend_caps use Numeric(10, 2) — zero is the reliable hard block.
    patched = await client.patch(
        f"/workspaces/{ws_id}/spend",
        headers=headers,
        json={"daily_cap_usd": 0.0, "monthly_cap_usd": 0.0},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["monthly_cap_usd"] == 0.0
    blocked = await client.post(
        f"/workspaces/{ws_id}/content-jobs",
        headers=headers,
        json={"topic": "should not land in review"},
    )
    assert blocked.status_code == 402, blocked.text
    gates = await client.get(
        f"/workspaces/{ws_id}/review-gates?status=awaiting", headers=headers
    )
    assert gates.status_code == 200
    assert gates.json() == []


@pytest.mark.asyncio
async def test_daily_cap_still_enforced():
    async with AsyncSessionLocal() as session:
        ws, user_id, item = await _user_workspace(session)
        await session.execute(
            text(
                "UPDATE spend_caps SET daily_cap_usd = 1, monthly_cap_usd = 1000 "
                "WHERE workspace_id = :ws"
            ),
            {"ws": str(ws.id)},
        )
        session.add(
            SpendLog(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                provider="draft_desk",
                stage=ContentStage.SCRIPTING,
                cost_usd=Decimal("0.90"),
                occurred_at=datetime.now(UTC),
            )
        )
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            content_item_id=item.id,
            status=PipelineRunStatus.RUNNING,
            correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()
        reservation = await controller.reserve_spend(
            session,
            run=run,
            stage="scripting",
            provider="draft_desk",
            estimated_cost_usd=Decimal("0.20"),
        )
        assert reservation is None
        assert run.status == PipelineRunStatus.PAUSED
