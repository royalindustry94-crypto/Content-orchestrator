"""Workspace-scoped Strategist and Strategy Auditor V1 routes."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.strategy import (
    StrategyAuditOut,
    StrategyBriefDetailOut,
    StrategyBriefOut,
    StrategyRunCreate,
    StrategyRunOut,
    StrategySummaryOut,
    WriterGateOut,
)
from app.services import strategy

router = APIRouter(prefix="/workspaces/{workspace_id}/strategy", tags=["strategist"])


def _not_found(detail: str = "strategy record not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post("/runs", response_model=StrategyRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    workspace_id: uuid.UUID,
    payload: StrategyRunCreate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> StrategyRunOut:
    del membership
    try:
        return await strategy.create_manual_run(
            db, workspace_id=workspace_id, actor_id=uuid.UUID(user.id), payload=payload
        )
    except strategy.StrategyGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/runs", response_model=list[StrategyRunOut])
async def runs(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[StrategyRunOut]:
    del membership
    return await strategy.list_runs(db, workspace_id=workspace_id)


@router.get("/runs/{run_id}", response_model=StrategyRunOut)
async def run_detail(
    workspace_id: uuid.UUID,
    run_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategyRunOut:
    del membership
    run = await strategy.get_run(db, workspace_id=workspace_id, run_id=run_id)
    if run is None:
        raise _not_found("strategy run not found")
    return run


@router.get("/summary", response_model=StrategySummaryOut)
async def strategy_summary(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategySummaryOut:
    del membership
    return StrategySummaryOut(**(await strategy.summary(db, workspace_id=workspace_id)))


@router.get("/briefs", response_model=list[StrategyBriefOut])
async def briefs(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[StrategyBriefOut]:
    del membership
    return await strategy.list_briefs(db, workspace_id=workspace_id)


@router.get("/briefs/{brief_id}", response_model=StrategyBriefDetailOut)
async def brief_detail(
    workspace_id: uuid.UUID,
    brief_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategyBriefDetailOut:
    del membership
    brief = await strategy.get_brief(db, workspace_id=workspace_id, brief_id=brief_id)
    if brief is None:
        raise _not_found("strategy brief not found")
    source_ids = await strategy.brief_opportunity_ids(
        db, workspace_id=workspace_id, brief_id=brief_id
    )
    audit = await strategy.latest_audit(db, workspace_id=workspace_id, brief_id=brief_id)
    return StrategyBriefDetailOut(
        brief=StrategyBriefOut.model_validate(brief),
        source_opportunity_ids=source_ids,
        latest_audit=StrategyAuditOut.model_validate(audit) if audit else None,
    )


@router.get("/briefs/{brief_id}/audit", response_model=StrategyAuditOut | None)
async def audit_detail(
    workspace_id: uuid.UUID,
    brief_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategyAuditOut | None:
    del membership
    brief = await strategy.get_brief(db, workspace_id=workspace_id, brief_id=brief_id)
    if brief is None:
        raise _not_found("strategy brief not found")
    audit = await strategy.latest_audit(db, workspace_id=workspace_id, brief_id=brief_id)
    return StrategyAuditOut.model_validate(audit) if audit else None


@router.post("/briefs/{brief_id}/audit", response_model=StrategyAuditOut)
async def run_audit(
    workspace_id: uuid.UUID,
    brief_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategyAuditOut:
    del membership
    try:
        return await strategy.audit_brief(db, workspace_id=workspace_id, brief_id=brief_id)
    except LookupError as exc:
        raise _not_found(str(exc)) from exc


@router.post("/briefs/{brief_id}/send-to-writer", response_model=WriterGateOut)
async def send_to_writer(
    workspace_id: uuid.UUID,
    brief_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> WriterGateOut:
    del membership
    try:
        return WriterGateOut(
            **(await strategy.writer_gate(db, workspace_id=workspace_id, brief_id=brief_id))
        )
    except LookupError as exc:
        raise _not_found(str(exc)) from exc
    except strategy.StrategyAuditGateError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
