"""Workspace-scoped Content Department V1 routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.content_department import (
    ContentDepartmentRunCreate,
    ContentDepartmentRunOut,
    ContentDepartmentSummaryOut,
    ContentPackageDetailOut,
    ContentPackageOut,
    ProducerGateOut,
)
from app.services import content_department

router = APIRouter(
    prefix="/workspaces/{workspace_id}/content-department", tags=["content-department"]
)


def _not_found(detail: str = "content department record not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post("/runs", response_model=ContentDepartmentRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    workspace_id: uuid.UUID,
    payload: ContentDepartmentRunCreate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> ContentDepartmentRunOut:
    del membership
    try:
        return await content_department.create_manual_run(
            db, workspace_id=workspace_id, actor_id=uuid.UUID(user.id), payload=payload
        )
    except content_department.ContentDepartmentGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/runs/{run_id}", response_model=ContentDepartmentRunOut)
async def run_detail(
    workspace_id: uuid.UUID,
    run_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ContentDepartmentRunOut:
    del membership
    run = await content_department.get_run(db, workspace_id=workspace_id, run_id=run_id)
    if run is None:
        raise _not_found("content department run not found")
    return run


@router.get("/summary", response_model=ContentDepartmentSummaryOut)
async def department_summary(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ContentDepartmentSummaryOut:
    del membership
    return ContentDepartmentSummaryOut(
        **(await content_department.summary(db, workspace_id=workspace_id))
    )


@router.get("/packages", response_model=list[ContentPackageOut])
async def packages(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[ContentPackageOut]:
    del membership
    return await content_department.list_packages(db, workspace_id=workspace_id)


@router.get("/packages/{package_id}", response_model=ContentPackageDetailOut)
async def package_detail(
    workspace_id: uuid.UUID,
    package_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ContentPackageDetailOut:
    del membership
    try:
        return ContentPackageDetailOut(
            **(
                await content_department.package_detail(
                    db, workspace_id=workspace_id, package_id=package_id
                )
            )
        )
    except content_department.ContentDepartmentNotFoundError as exc:
        raise _not_found(str(exc)) from exc


@router.get("/packages/{package_id}/producer-gate", response_model=ProducerGateOut)
async def producer_gate(
    workspace_id: uuid.UUID,
    package_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ProducerGateOut:
    del membership
    try:
        return ProducerGateOut(
            **(
                await content_department.producer_gate(
                    db, workspace_id=workspace_id, package_id=package_id
                )
            )
        )
    except content_department.ContentDepartmentNotFoundError as exc:
        raise _not_found(str(exc)) from exc
    except content_department.ContentDepartmentGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
