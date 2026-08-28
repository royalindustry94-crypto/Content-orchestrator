from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.authorization import require_workspace_admin
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.compliance import (
    ArtifactPublicationEligibilityResponse,
    ChiefAuditResponse,
    ComplianceAuditResponse,
    ComplianceRunRequest,
    ComplianceSummaryResponse,
    HumanReviewPackageResponse,
)
from app.services import compliance

router = APIRouter(
    prefix="/workspaces/{workspace_id}/compliance", tags=["compliance-chief-auditor"]
)


def _audit(row: object) -> ComplianceAuditResponse:
    return ComplianceAuditResponse(
        id=row.id,
        final_artifact_id=row.final_artifact_id,
        artifact_hash=row.artifact_hash,
        content_version_id=row.content_version_id,
        target_platform=row.target_platform,
        status=row.status,
        risk_level=row.risk_level,
        rights_status=row.rights_status,
        provider_state=row.provider_state,
        findings=row.findings,
        required_disclosures=row.required_disclosures,
        cost_usd=row.cost_usd,
        test_data=row.test_data,
    )


@router.post("/runs", response_model=ComplianceAuditResponse, status_code=status.HTTP_201_CREATED)
async def run_compliance(
    workspace_id: uuid.UUID,
    payload: ComplianceRunRequest,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> ComplianceAuditResponse:
    del membership
    try:
        return _audit(
            await compliance.create_compliance_run(
                db,
                workspace_id=workspace_id,
                actor_id=uuid.UUID(user.id),
                final_artifact_id=payload.final_artifact_id,
                target_platform=payload.target_platform,
                max_provider_calls=payload.max_provider_calls,
                max_verification_calls=payload.max_verification_calls,
                max_tokens=payload.max_tokens,
                max_cost_usd=payload.max_cost_usd,
                max_attempts=payload.max_attempts,
            )
        )
    except compliance.ComplianceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except compliance.ComplianceGateError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/summary", response_model=ComplianceSummaryResponse)
async def get_summary(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> ComplianceSummaryResponse:
    del membership
    return ComplianceSummaryResponse(**(await compliance.summary(db, workspace_id=workspace_id)))


@router.get("/audits", response_model=list[ComplianceAuditResponse])
async def get_audits(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[ComplianceAuditResponse]:
    del membership
    return [_audit(row) for row in await compliance.list_audits(db, workspace_id=workspace_id)]


@router.get("/chief-audits", response_model=list[ChiefAuditResponse])
async def get_chief_audits(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[ChiefAuditResponse]:
    del membership
    rows = await compliance.list_chief_audits(db, workspace_id=workspace_id)
    return [
        ChiefAuditResponse(
            id=row.id,
            final_artifact_id=row.final_artifact_id,
            artifact_hash=row.artifact_hash,
            status=row.status,
            lineage_status=row.lineage_status,
            version_integrity_status=row.version_integrity_status,
            cost_reconciliation_status=row.cost_reconciliation_status,
            provider_reconciliation_status=row.provider_reconciliation_status,
            blockers=row.blockers,
            test_data=row.test_data,
        )
        for row in rows
    ]


@router.get("/human-review-packages", response_model=list[HumanReviewPackageResponse])
async def get_human_review_packages(
    workspace_id: uuid.UUID,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    db: AsyncSession = Depends(get_current_session),
) -> list[HumanReviewPackageResponse]:
    del membership
    rows = await compliance.list_review_packages(db, workspace_id=workspace_id)
    return [
        HumanReviewPackageResponse(
            id=row.id,
            final_artifact_id=row.final_artifact_id,
            artifact_hash=row.artifact_hash,
            content_version_id=row.content_version_id,
            target_platform=row.target_platform,
            review_gate_id=row.review_gate_id,
            warnings=row.warnings,
            required_disclosures=row.required_disclosures,
            total_cost_usd=row.total_cost_usd,
            test_data=row.test_data,
        )
        for row in rows
    ]


@router.post(
    "/artifacts/{final_artifact_id}/publication-eligibility",
    response_model=ArtifactPublicationEligibilityResponse,
)
async def determine_publication_eligibility(
    workspace_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    target_platform: str,
    membership: WorkspaceMembership = Depends(require_workspace_admin),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
) -> ArtifactPublicationEligibilityResponse:
    del membership
    try:
        row = await compliance.publication_eligibility(
            db,
            workspace_id=workspace_id,
            actor_id=uuid.UUID(user.id),
            final_artifact_id=final_artifact_id,
            target_platform=target_platform,
        )
        return ArtifactPublicationEligibilityResponse(
            id=row.id,
            final_artifact_id=row.final_artifact_id,
            artifact_hash=row.artifact_hash,
            target_platform=row.target_platform,
            status=row.status,
            publication_eligible=row.publication_eligible,
            blocking_reasons=row.blocking_reasons,
            test_data=row.test_data,
        )
    except compliance.ComplianceNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
