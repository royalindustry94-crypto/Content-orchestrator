"""Workspace-admin Operations Dashboard read APIs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.authorization import require_workspace_admin
from app.db.session import AsyncSessionLocal
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.operations_dashboard import (
    AlertsOut,
    ExecutiveDashboardOut,
    PipelineMonitorOut,
    WorkerMonitorOut,
)
from app.services import operations_dashboard

router = APIRouter(
    prefix="/workspaces/{workspace_id}/operations",
    tags=["operations-dashboard"],
)


@router.get("/executive", response_model=ExecutiveDashboardOut)
async def executive_dashboard(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> ExecutiveDashboardOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.executive(session, workspace_id)


@router.get("/workers", response_model=WorkerMonitorOut)
async def worker_monitor(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> WorkerMonitorOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.workers(session, workspace_id)


@router.get("/pipelines", response_model=PipelineMonitorOut)
async def pipeline_monitor(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> PipelineMonitorOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.pipelines(session, workspace_id)


@router.get("/alerts", response_model=AlertsOut)
async def alerts(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> AlertsOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.alerts(session, workspace_id)
