"""Workspace-scoped Producer and Media QA V1 routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.production import FinalArtifact, MediaQaResult, ProductionReadiness
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.production import (
    FinalArtifactOut,
    MediaQaOut,
    ProductionDetailOut,
    ProductionReadinessOut,
    ProductionRunCreate,
    ProductionRunOut,
    ProductionSummaryOut,
)
from app.services import production

router = APIRouter(prefix="/workspaces/{workspace_id}/production", tags=["producer-media-qa"])


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post("/runs", response_model=ProductionRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    workspace_id: uuid.UUID,
    payload: ProductionRunCreate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> ProductionRunOut:
    del membership
    try:
        return await production.create_production_run(
            db,
            workspace_id=workspace_id,
            actor_id=uuid.UUID(user.id),
            content_package_id=payload.content_package_id,
            target_platform=payload.target_platform,
            target_format=payload.target_format,
            target_duration_seconds=payload.target_duration_seconds,
            max_provider_calls=payload.max_provider_calls,
            max_render_calls=payload.max_render_calls,
            max_cost_usd=payload.max_cost_usd,
            max_attempts=payload.max_attempts,
            max_repair_cycles=payload.max_repair_cycles,
            timeout_seconds=payload.timeout_seconds,
        )
    except production.ProductionNotFoundError as exc:
        raise _not_found(str(exc)) from exc
    except production.ProductionEligibilityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/summary", response_model=ProductionSummaryOut)
async def production_summary(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ProductionSummaryOut:
    del membership
    return ProductionSummaryOut(**(await production.summary(db, workspace_id=workspace_id)))


@router.get("/runs", response_model=list[ProductionRunOut])
async def runs(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[ProductionRunOut]:
    del membership
    return await production.list_jobs(db, workspace_id=workspace_id)


@router.get("/runs/{production_job_id}", response_model=ProductionDetailOut)
async def run_detail(
    workspace_id: uuid.UUID,
    production_job_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ProductionDetailOut:
    del membership
    try:
        detail = await production.job_detail(
            db,
            workspace_id=workspace_id,
            production_job_id=production_job_id,
        )
    except production.ProductionNotFoundError as exc:
        raise _not_found(str(exc)) from exc
    return ProductionDetailOut(
        job=ProductionRunOut.model_validate(detail["job"]),
        assets=detail["assets"],
        artifacts=detail["artifacts"],
        media_qa=detail["media_qa"],
        repairs=detail["repairs"],
        readiness=detail["readiness"],
    )


@router.get("/artifacts/{artifact_id}", response_model=FinalArtifactOut)
async def artifact_detail(
    workspace_id: uuid.UUID,
    artifact_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> FinalArtifactOut:
    del membership
    artifact = (
        await db.execute(
            select(FinalArtifact).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.id == artifact_id,
            )
        )
    ).scalar_one_or_none()
    if artifact is None:
        raise _not_found("final artifact not found")
    return FinalArtifactOut.model_validate(artifact)


@router.get("/artifacts/{artifact_id}/media-qa", response_model=list[MediaQaOut])
async def artifact_qa(
    workspace_id: uuid.UUID,
    artifact_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[MediaQaOut]:
    del membership
    return (
        (
            await db.execute(
                select(MediaQaResult)
                .where(
                    MediaQaResult.workspace_id == workspace_id,
                    MediaQaResult.final_artifact_id == artifact_id,
                )
                .order_by(MediaQaResult.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


@router.get("/artifacts/{artifact_id}/readiness", response_model=ProductionReadinessOut | None)
async def artifact_readiness(
    workspace_id: uuid.UUID,
    artifact_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ProductionReadinessOut | None:
    del membership
    row = (
        await db.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact_id,
            )
        )
    ).scalar_one_or_none()
    return ProductionReadinessOut.model_validate(row) if row else None
