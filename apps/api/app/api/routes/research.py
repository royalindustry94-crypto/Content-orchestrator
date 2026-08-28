"""Workspace-scoped Scout and Research Auditor V1 endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.research import (
    EvidenceOut,
    OpportunityDetailOut,
    OpportunityOut,
    ResearchAuditOut,
    ResearchRunCreate,
    ResearchRunOut,
    ResearchSummaryOut,
    SourceOut,
    StrategistGateOut,
)
from app.services import research

router = APIRouter(
    prefix="/workspaces/{workspace_id}/research", tags=["scout-research"]
)


def _not_found(detail: str = "research record not found") -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.post(
    "/runs", response_model=ResearchRunOut, status_code=status.HTTP_201_CREATED
)
async def create_run(
    workspace_id: uuid.UUID,
    payload: ResearchRunCreate,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> ResearchRunOut:
    del membership
    return await research.create_manual_run(
        db, workspace_id=workspace_id, actor_id=uuid.UUID(user.id), payload=payload
    )


@router.get("/runs", response_model=list[ResearchRunOut])
async def runs(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[ResearchRunOut]:
    del membership
    return await research.list_runs(db, workspace_id=workspace_id)


@router.get("/runs/{run_id}", response_model=ResearchRunOut)
async def run_detail(
    workspace_id: uuid.UUID,
    run_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ResearchRunOut:
    del membership
    run = await research.get_run(db, workspace_id=workspace_id, run_id=run_id)
    if run is None:
        raise _not_found("research run not found")
    return run


@router.get("/summary", response_model=ResearchSummaryOut)
async def research_summary(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ResearchSummaryOut:
    del membership
    return ResearchSummaryOut(**(await research.summary(db, workspace_id=workspace_id)))


@router.get("/opportunities", response_model=list[OpportunityOut])
async def opportunities(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[OpportunityOut]:
    del membership
    return await research.list_opportunities(db, workspace_id=workspace_id)


@router.get("/opportunities/{opportunity_id}", response_model=OpportunityDetailOut)
async def opportunity_detail(
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> OpportunityDetailOut:
    del membership
    opportunity = await research.get_opportunity(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if opportunity is None:
        raise _not_found("opportunity not found")
    evidence = await research.opportunity_evidence(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    audit = await research.latest_audit(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    return OpportunityDetailOut(
        opportunity=OpportunityOut.model_validate(opportunity),
        evidence=[
            EvidenceOut(
                source=SourceOut.model_validate(source),
                claim_supported=link.claim_supported,
                relevance=link.relevance,
                contradiction_flag=link.contradiction_flag,
            )
            for link, source in evidence
        ],
        latest_audit=ResearchAuditOut.model_validate(audit) if audit else None,
    )


@router.get("/opportunities/{opportunity_id}/sources", response_model=list[EvidenceOut])
async def sources(
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[EvidenceOut]:
    del membership
    opportunity = await research.get_opportunity(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if opportunity is None:
        raise _not_found("opportunity not found")
    evidence = await research.opportunity_evidence(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    return [
        EvidenceOut(
            source=SourceOut.model_validate(source),
            claim_supported=link.claim_supported,
            relevance=link.relevance,
            contradiction_flag=link.contradiction_flag,
        )
        for link, source in evidence
    ]


@router.get(
    "/opportunities/{opportunity_id}/audit", response_model=ResearchAuditOut | None
)
async def audit_detail(
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ResearchAuditOut | None:
    del membership
    opportunity = await research.get_opportunity(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if opportunity is None:
        raise _not_found("opportunity not found")
    audit = await research.latest_audit(
        db, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    return ResearchAuditOut.model_validate(audit) if audit else None


@router.post("/opportunities/{opportunity_id}/audit", response_model=ResearchAuditOut)
async def run_audit(
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ResearchAuditOut:
    del membership
    try:
        return await research.audit_opportunity(
            db, workspace_id=workspace_id, opportunity_id=opportunity_id
        )
    except LookupError as exc:
        raise _not_found(str(exc)) from exc


@router.post(
    "/opportunities/{opportunity_id}/send-to-strategist",
    response_model=StrategistGateOut,
)
async def send_to_strategist(
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> StrategistGateOut:
    del membership
    try:
        return StrategistGateOut(
            **(
                await research.strategist_gate(
                    db, workspace_id=workspace_id, opportunity_id=opportunity_id
                )
            )
        )
    except LookupError as exc:
        raise _not_found(str(exc)) from exc
    except research.ResearchGateError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        ) from exc
