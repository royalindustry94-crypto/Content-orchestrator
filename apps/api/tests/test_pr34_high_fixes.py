"""Regression tests for PR #34 High findings H-1…H-4 (+ M-2 webhook race)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text

from app.core.config import Settings
from app.db.session import AsyncSessionLocal
from app.models.billing import WorkspaceBilling
from app.models.content import ContentItem
from app.models.enums import ContentStage, ContentStatus, PipelineRunStatus, ReservationStatus
from app.models.pipeline import PipelineRun
from app.models.spend import SpendLog, SpendReservation
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.orchestration import controller
from app.services import billing as billing_service
from app.services.spend import ensure_default_spend_cap


def _base_settings_kwargs(**overrides) -> dict:
    kwargs = {
        "database_url": "postgresql://postgres:postgres@127.0.0.1:5432/content_orchestrator_test",
        "app_database_url": (
            "postgresql://app_runtime:app_runtime@127.0.0.1:5432/content_orchestrator_test"
        ),
        "supabase_jwt_secret": "test-supabase-jwt-secret-0123456789abcdef",
        "environment": "development",
        "auth_mode": "supabase",
    }
    kwargs.update(overrides)
    return kwargs


def test_h1_auth_mode_defaults_to_supabase():
    settings = Settings(**_base_settings_kwargs())
    assert settings.auth_mode == "supabase"


def test_h1_production_rejects_local_auth_without_override():
    with pytest.raises(ValidationError, match="AUTH_MODE=local is forbidden"):
        Settings(
            **_base_settings_kwargs(
                environment="production",
                auth_mode="local",
                allow_local_auth_in_production=False,
            )
        )


def test_h1_production_allows_local_with_explicit_override():
    settings = Settings(
        **_base_settings_kwargs(
            environment="production",
            auth_mode="local",
            allow_local_auth_in_production=True,
        )
    )
    assert settings.auth_mode == "local"


async def _seed_workspace_item(session):
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
    ws = Workspace(id=uuid.uuid4(), name=f"pr34-{user_id}", created_by=user_id)
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
        topic="pr34 highs",
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()
    return ws, user_id, item


@pytest.mark.asyncio
async def test_h3_commit_spend_clamps_actual_to_reserved():
    async with AsyncSessionLocal() as session:
        ws, _user_id, item = await _seed_workspace_item(session)
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
            provider="openai",
            estimated_cost_usd=Decimal("0.50"),
        )
        assert reservation is not None
        await controller.commit_spend(
            session,
            run=run,
            reservation=reservation,
            actual_cost_usd=Decimal("999.99"),
        )
        await session.commit()
        await session.refresh(reservation)
        assert reservation.status == ReservationStatus.COMMITTED
        log = (
            await session.execute(
                select(SpendLog).where(SpendLog.workspace_id == ws.id)
            )
        ).scalar_one()
        assert Decimal(str(log.cost_usd)) == Decimal("0.50")


@pytest.mark.asyncio
async def test_h4_reserve_retry_releases_prior_open_reservation():
    async with AsyncSessionLocal() as session:
        ws, _user_id, item = await _seed_workspace_item(session)
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            content_item_id=item.id,
            status=PipelineRunStatus.RUNNING,
            correlation_id=uuid.uuid4(),
        )
        session.add(run)
        await session.flush()
        first = await controller.reserve_spend(
            session,
            run=run,
            stage="scripting",
            provider="openai",
            estimated_cost_usd=Decimal("0.10"),
        )
        assert first is not None
        second = await controller.reserve_spend(
            session,
            run=run,
            stage="scripting",
            provider="openai",
            estimated_cost_usd=Decimal("0.10"),
        )
        assert second is not None
        assert second.id != first.id
        await session.commit()
        await session.refresh(first)
        await session.refresh(second)
        assert first.status == ReservationStatus.RELEASED
        assert second.status == ReservationStatus.RESERVED
        open_rows = (
            await session.execute(
                select(SpendReservation).where(
                    SpendReservation.pipeline_run_id == run.id,
                    SpendReservation.stage == "scripting",
                    SpendReservation.status == ReservationStatus.RESERVED,
                )
            )
        ).scalars().all()
        assert len(open_rows) == 1
        assert open_rows[0].id == second.id


@pytest.mark.asyncio
async def test_h2_checkout_does_not_entitle_without_subscription():
    workspace_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        user_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO profiles (id, email) VALUES (:id, :email) "
                "ON CONFLICT (id) DO NOTHING"
            ),
            {"id": str(user_id), "email": f"{user_id}@ex.com"},
        )
        await session.execute(
            text(
                "INSERT INTO workspaces (id, name, created_by) VALUES (:id, :name, :by)"
            ),
            {"id": str(workspace_id), "name": "H2 WS", "by": str(user_id)},
        )
        await session.commit()

    event = {
        "id": f"evt_h2_{uuid.uuid4().hex}",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "customer": f"cus_h2_{uuid.uuid4().hex[:8]}",
                "subscription": f"sub_h2_{uuid.uuid4().hex[:8]}",
                "payment_status": "unpaid",
                "metadata": {"workspace_id": str(workspace_id)},
            }
        },
    }
    async with AsyncSessionLocal() as session:
        result = await billing_service.process_stripe_event(session, event=event)
        await session.commit()
    assert result["status"] == "processed"
    async with AsyncSessionLocal() as session:
        row = await session.get(WorkspaceBilling, workspace_id)
        assert row is not None
        assert row.plan == "none"
        assert row.status == "inactive"
        assert not billing_service.is_entitled(row, billing_enabled=True)
