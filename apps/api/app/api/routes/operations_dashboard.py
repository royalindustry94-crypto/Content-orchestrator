"""Workspace-admin Operations Dashboard APIs (V1 + V2 Founder Control Center)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import AsyncSessionLocal
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.operations_dashboard import (
    AlertsOut,
    CustomersOut,
    ExecutiveDashboardOut,
    GitHubOut,
    LeadCreate,
    LeadOut,
    LeadsOut,
    LeadUpdate,
    NotificationsOut,
    PipelineMonitorOut,
    SpendOut,
    WorkerMonitorOut,
)
from app.services import github_status, operations_dashboard

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


@router.get("/notifications", response_model=NotificationsOut)
async def notifications(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> NotificationsOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.notifications(session, workspace_id)


@router.get("/leads", response_model=LeadsOut)
async def list_leads(
    workspace_id: uuid.UUID,
    search: str | None = Query(default=None, max_length=200),
    status_filter: str | None = Query(default=None, alias="status", max_length=32),
    source: str | None = Query(default=None, max_length=100),
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> LeadsOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.list_leads(
            session,
            workspace_id,
            search=search,
            status=status_filter,
            source=source,
        )


@router.post("/leads", response_model=LeadOut, status_code=status.HTTP_201_CREATED)
async def create_lead(
    workspace_id: uuid.UUID,
    payload: LeadCreate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> LeadOut:
    try:
        async with AsyncSessionLocal() as session:
            return await operations_dashboard.create_lead(session, workspace_id, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.patch("/leads/{lead_id}", response_model=LeadOut)
async def update_lead(
    workspace_id: uuid.UUID,
    lead_id: uuid.UUID,
    payload: LeadUpdate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> LeadOut:
    try:
        async with AsyncSessionLocal() as session:
            lead = await operations_dashboard.update_lead(
                session, workspace_id, lead_id, payload
            )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc
    if lead is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")
    return lead


@router.get("/customers", response_model=CustomersOut)
async def customers(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
) -> CustomersOut:
    del workspace_id  # authz scoped; customers are admin-owned workspaces
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.customers(
            session, admin_user_id=uuid.UUID(user.id)
        )


@router.get("/spend", response_model=SpendOut)
async def spend_dashboard(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> SpendOut:
    async with AsyncSessionLocal() as session:
        return await operations_dashboard.spend(session, workspace_id)


@router.get("/github", response_model=GitHubOut)
async def github_dashboard(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
) -> GitHubOut:
    del workspace_id, membership
    return await github_status.github_status()
