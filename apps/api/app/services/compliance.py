"""Bounded Compliance and Chief Auditor V1 service.

Compliance assessment goes through the configured pipeline provider; without
one, requests persist an accountable blocked/no-provider state. The Chief
Auditor is not a provider call: it independently reconciles the recorded gate
manifest against what actually happened, and it refuses to pass anything to
Human Review with a gate missing.

A Chief Auditor pass opens the Human Review Gate. It never publishes: external
publishing stays disabled in ``publication_eligibility`` regardless of provider.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compliance import (
    ArtifactPublicationEligibility,
    ArtifactRightsEvidence,
    AuditGateManifest,
    ChiefAudit,
    ComplianceAudit,
    ComplianceInvalidation,
    HumanReviewPackage,
)
from app.models.content import ContentItem, ContentVersion
from app.models.content_department import ContentAudit, ContentPackage
from app.models.production import FinalArtifact, MediaQaResult, ProductionJob, ProductionReadiness
from app.models.research import ResearchAudit
from app.models.strategy import StrategyAudit, StrategyBriefOpportunity
from app.orchestration import outbox
from app.providers import ComplianceRequest, get_pipeline_provider
from app.services import content_desk

COMPLIANCE_WORKER_ID = "compliance"
CHIEF_AUDITOR_WORKER_ID = "chief_auditor"


class ComplianceNotFoundError(Exception):
    pass


class ComplianceGateError(Exception):
    pass


DEFAULT_GATES = [
    "research_audit",
    "strategy_audit",
    "language_audit",
    "fact_audit",
    "brand_audit",
    "originality_audit",
    "media_qa",
    "compliance",
    "chief_audit",
    "human_review",
]


async def _artifact(
    session: AsyncSession, workspace_id: uuid.UUID, artifact_id: uuid.UUID
) -> FinalArtifact:
    artifact = (
        await session.execute(
            select(FinalArtifact).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.id == artifact_id,
            )
        )
    ).scalar_one_or_none()
    if artifact is None:
        raise ComplianceNotFoundError("final artifact not found")
    return artifact


async def create_compliance_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    target_platform: str,
    max_provider_calls: int,
    max_verification_calls: int,
    max_tokens: int,
    max_cost_usd: Decimal,
    max_attempts: int,
) -> ComplianceAudit:
    artifact = await _artifact(session, workspace_id, final_artifact_id)
    media_qa = (
        (
            await session.execute(
                select(MediaQaResult).where(
                    MediaQaResult.workspace_id == workspace_id,
                    MediaQaResult.final_artifact_id == artifact.id,
                    MediaQaResult.artifact_hash == artifact.artifact_hash,
                )
            )
        )
        .scalars()
        .first()
    )
    rights = (
        (
            await session.execute(
                select(ArtifactRightsEvidence).where(
                    ArtifactRightsEvidence.workspace_id == workspace_id,
                    ArtifactRightsEvidence.final_artifact_id == artifact.id,
                )
            )
        )
        .scalars()
        .first()
    )
    provider = get_pipeline_provider()
    input_snapshot = {
        "artifact_hash": artifact.artifact_hash,
        "media_qa": media_qa.status if media_qa else "missing",
        "rights": rights.rights_status if rights else "missing",
        "max_provider_calls": max_provider_calls,
        "max_verification_calls": max_verification_calls,
        "max_tokens": max_tokens,
        "max_cost_usd": str(max_cost_usd),
        "max_attempts": max_attempts,
    }
    if not provider.is_configured:
        audit = ComplianceAudit(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            final_artifact_id=artifact.id,
            artifact_hash=artifact.artifact_hash,
            content_version_id=artifact.content_version_id,
            target_platform=target_platform,
            compliance_worker_id=COMPLIANCE_WORKER_ID,
            input_snapshot=input_snapshot,
            status="blocked_provider_not_configured",
            risk_level="unknown",
            rights_status=rights.rights_status if rights else "unverified",
            findings=[{"code": "compliance_provider_not_configured", "severity": "blocker"}],
            provider_state=provider.state_label,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        session.add(audit)
        await session.flush()
        await outbox.emit(
            session,
            event_type="compliance.requested.not_configured",
            workspace_id=workspace_id,
            aggregate_type="compliance_audit",
            aggregate_id=audit.id,
            correlation_id=uuid.uuid4(),
            payload={
                "final_artifact_id": str(artifact.id),
                "artifact_hash": artifact.artifact_hash,
            },
            produced_by="compliance_v1",
        )
        return audit

    # Media QA bound to this exact hash is a precondition, not something the
    # compliance provider is trusted to re-derive.
    if media_qa is None or media_qa.status != "pass":
        raise ComplianceGateError(
            "an independent Media QA pass bound to this exact artifact hash is required "
            "before compliance assessment"
        )

    version = await session.get(ContentVersion, artifact.content_version_id)
    try:
        result = await provider.compliance(
            ComplianceRequest(
                workspace_id=workspace_id,
                target_platform=target_platform,
                artifact_hash=artifact.artifact_hash,
                script_hook=(version.script_hook if version else "") or "",
                script_body=(version.script_body if version else "") or "",
                script_cta=(version.script_cta if version else "") or "",
            )
        )
    except Exception as exc:  # a failed assessment is a failure, not a pass
        audit = ComplianceAudit(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            final_artifact_id=artifact.id,
            artifact_hash=artifact.artifact_hash,
            content_version_id=artifact.content_version_id,
            target_platform=target_platform,
            compliance_worker_id=COMPLIANCE_WORKER_ID,
            input_snapshot=input_snapshot,
            status="failed",
            risk_level="unknown",
            rights_status="unverified",
            findings=[{"code": "compliance_provider_failed", "severity": "blocker"}],
            provider_state=provider.state_label,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
        audit.input_snapshot = {**input_snapshot, "error": str(exc)}
        session.add(audit)
        await session.flush()
        return audit

    if rights is None:
        session.add(
            ArtifactRightsEvidence(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                final_artifact_id=artifact.id,
                origin=provider.state_label,
                provider_or_source=provider.name,
                license_or_right_basis=result.rights_basis,
                generation_record={"provider": provider.name, "mode": provider.state_label},
                modification_lineage={"artifact_hash": artifact.artifact_hash},
                rights_status=result.rights_status,
                created_by=actor_id,
            )
        )
        await session.flush()

    blockers = [item for item in result.findings if item.get("severity") == "blocker"]
    status_value = "blocked" if blockers or result.rights_status != "verified" else "pass"
    audit = ComplianceAudit(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        target_platform=target_platform,
        policy_version=result.policy_version,
        compliance_worker_id=COMPLIANCE_WORKER_ID,
        input_snapshot=input_snapshot,
        status=status_value,
        risk_level=result.risk_level,
        rights_status=result.rights_status,
        findings=list(result.findings),
        evidence=list(result.evidence),
        required_disclosures=list(result.required_disclosures),
        reused_content_risk=result.reused_content_risk,
        monetization_risk=result.monetization_risk,
        provider_state=provider.state_label,
        provider_calls_used=result.usage.calls,
        token_count=result.usage.tokens,
        cost_usd=result.usage.cost_usd,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(audit)
    await session.flush()
    readiness = (
        await session.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact.id,
            )
        )
    ).scalar_one_or_none()
    if readiness is not None:
        readiness.compliance_state = status_value
        readiness.updated_by = actor_id
    await outbox.emit(
        session,
        event_type=f"compliance.assessed.{status_value}",
        workspace_id=workspace_id,
        aggregate_type="compliance_audit",
        aggregate_id=audit.id,
        correlation_id=uuid.uuid4(),
        payload={
            "final_artifact_id": str(artifact.id),
            "artifact_hash": artifact.artifact_hash,
            "provider": provider.name,
        },
        produced_by="compliance_v1",
    )
    return audit


async def summary(session: AsyncSession, *, workspace_id: uuid.UUID) -> dict:
    rows = (
        (
            await session.execute(
                select(ComplianceAudit).where(ComplianceAudit.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    packages = (
        (
            await session.execute(
                select(HumanReviewPackage).where(HumanReviewPackage.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    eligibility = (
        (
            await session.execute(
                select(ArtifactPublicationEligibility).where(
                    ArtifactPublicationEligibility.workspace_id == workspace_id
                )
            )
        )
        .scalars()
        .all()
    )
    provider = get_pipeline_provider()
    return {
        "provider_state": provider.state_label,
        # Platform policy freshness needs a live policy source; a configured
        # content provider does not establish it.
        "policy_state": "freshness_unverified",
        "compliance_audits": len(rows),
        "passed": sum(row.status == "pass" for row in rows),
        "blocked": sum(row.status != "pass" for row in rows),
        "human_review_packages": len(packages),
        "publication_eligible": sum(row.publication_eligible for row in eligibility),
        "provider_cost_usd": sum((Decimal(str(row.cost_usd)) for row in rows), Decimal("0")),
        "real_provider_mode": False,
        "test_fixture_mode": False,
    }


async def list_audits(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[ComplianceAudit]:
    return (
        (
            await session.execute(
                select(ComplianceAudit)
                .where(ComplianceAudit.workspace_id == workspace_id)
                .order_by(ComplianceAudit.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def list_chief_audits(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[ChiefAudit]:
    return (
        (
            await session.execute(
                select(ChiefAudit)
                .where(ChiefAudit.workspace_id == workspace_id)
                .order_by(ChiefAudit.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def list_review_packages(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> list[HumanReviewPackage]:
    return (
        (
            await session.execute(
                select(HumanReviewPackage)
                .where(HumanReviewPackage.workspace_id == workspace_id)
                .order_by(HumanReviewPackage.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def ensure_gate_manifest(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    test_data: bool = False,
) -> AuditGateManifest:
    """Idempotently provision the workspace's required-gate manifest.

    The manifest is what the Chief Auditor reconciles against, so it is stored
    rather than recomputed: a gate cannot be quietly dropped from the required
    set between the time content was produced and the time it was audited.
    """
    existing = (
        await session.execute(
            select(AuditGateManifest).where(
                AuditGateManifest.workspace_id == workspace_id,
                AuditGateManifest.content_type == "short_form_media",
                AuditGateManifest.manifest_version == 1,
            )
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    manifest = AuditGateManifest(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_type="short_form_media",
        manifest_version=1,
        required_gates=DEFAULT_GATES,
        requirements={"all_gates_mandatory": True},
        created_by=actor_id,
        test_data=test_data,
    )
    session.add(manifest)
    await session.flush()
    return manifest


async def create_test_manifest(
    session: AsyncSession, *, workspace_id: uuid.UUID, actor_id: uuid.UUID
) -> AuditGateManifest:
    """Test-only alias retained for the existing fixture suites."""
    return await ensure_gate_manifest(
        session, workspace_id=workspace_id, actor_id=actor_id, test_data=True
    )


async def _gate_states(
    session: AsyncSession, *, workspace_id: uuid.UUID, artifact: FinalArtifact
) -> dict[str, str]:
    """Resolve the real state of every required gate for one artifact.

    Each lookup is bound to the artifact hash or the exact content version, so
    an audit granted to different bytes can never be counted here.
    """
    states = dict.fromkeys(DEFAULT_GATES, "missing")

    job = (
        await session.execute(
            select(ProductionJob).where(
                ProductionJob.workspace_id == workspace_id,
                ProductionJob.id == artifact.production_job_id,
            )
        )
    ).scalar_one_or_none()
    package = None
    if job is not None:
        package = (
            await session.execute(
                select(ContentPackage).where(
                    ContentPackage.workspace_id == workspace_id,
                    ContentPackage.id == job.content_package_id,
                )
            )
        ).scalar_one_or_none()

    if package is not None:
        opportunity_ids = list(
            (
                await session.execute(
                    select(StrategyBriefOpportunity.opportunity_id).where(
                        StrategyBriefOpportunity.workspace_id == workspace_id,
                        StrategyBriefOpportunity.strategy_brief_id == package.strategy_brief_id,
                    )
                )
            ).scalars()
        )
        research_states = []
        for opportunity_id in opportunity_ids:
            audit = (
                await session.execute(
                    select(ResearchAudit)
                    .where(
                        ResearchAudit.workspace_id == workspace_id,
                        ResearchAudit.opportunity_id == opportunity_id,
                    )
                    .order_by(ResearchAudit.checked_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            research_states.append(audit.state if audit else "missing")
        if research_states:
            states["research_audit"] = (
                "pass" if all(state == "pass" for state in research_states) else "blocked"
            )

        strategy_audit = (
            await session.execute(
                select(StrategyAudit)
                .where(
                    StrategyAudit.workspace_id == workspace_id,
                    StrategyAudit.strategy_brief_id == package.strategy_brief_id,
                )
                .order_by(StrategyAudit.checked_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if strategy_audit is not None:
            states["strategy_audit"] = strategy_audit.state

        for auditor_type in ("language", "fact", "brand", "originality"):
            content_audit = (
                await session.execute(
                    select(ContentAudit)
                    .where(
                        ContentAudit.workspace_id == workspace_id,
                        ContentAudit.content_package_id == package.id,
                        ContentAudit.content_version_id == artifact.content_version_id,
                        ContentAudit.auditor_type == auditor_type,
                    )
                    .order_by(ContentAudit.checked_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
            if content_audit is not None:
                states[f"{auditor_type}_audit"] = content_audit.state

    media = (
        await session.execute(
            select(MediaQaResult).where(
                MediaQaResult.workspace_id == workspace_id,
                MediaQaResult.final_artifact_id == artifact.id,
                MediaQaResult.artifact_hash == artifact.artifact_hash,
            )
        )
    ).scalar_one_or_none()
    if media is not None:
        states["media_qa"] = media.status

    compliance = (
        await session.execute(
            select(ComplianceAudit)
            .where(
                ComplianceAudit.workspace_id == workspace_id,
                ComplianceAudit.final_artifact_id == artifact.id,
                ComplianceAudit.artifact_hash == artifact.artifact_hash,
            )
            .order_by(ComplianceAudit.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if compliance is not None:
        states["compliance"] = compliance.status

    # The Chief Auditor is the gate being evaluated, and Human Review is the
    # gate it can open. Neither is ever satisfied by this reconciliation.
    states["chief_audit"] = "in_progress"
    states["human_review"] = "pending"
    return states


async def run_chief_audit(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
) -> ChiefAudit:
    """Reconcile every required gate and, on a clean pass, open Human Review.

    This is not a provider call. It re-derives each gate's state from stored
    records rather than trusting any upstream stage's own report of itself.
    """
    artifact = await _artifact(session, workspace_id, final_artifact_id)
    manifest = await ensure_gate_manifest(
        session, workspace_id=workspace_id, actor_id=actor_id, test_data=artifact.test_data
    )
    states = await _gate_states(session, workspace_id=workspace_id, artifact=artifact)

    blockers = [
        f"{gate}_{states[gate]}"
        for gate in manifest.required_gates
        if gate not in {"chief_audit", "human_review"} and states.get(gate) != "pass"
    ]
    status_value = "pass_to_human_review" if not blockers else "blocked"
    complete = "complete" if not blockers else "incomplete"
    audit = ChiefAudit(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        gate_manifest_id=manifest.id,
        chief_auditor_worker_id=CHIEF_AUDITOR_WORKER_ID,
        gate_snapshot={"required": list(manifest.required_gates), "observed": states},
        lineage_status=complete,
        version_integrity_status=complete,
        cost_reconciliation_status=complete,
        provider_reconciliation_status=complete,
        warnings=[],
        blockers=blockers,
        evidence=[{"source": "persisted_gate_records", "artifact_hash": artifact.artifact_hash}],
        status=status_value,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_data=artifact.test_data,
    )
    session.add(audit)
    await session.flush()

    readiness = (
        await session.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact.id,
            )
        )
    ).scalar_one_or_none()
    if readiness is not None:
        readiness.chief_audit_state = status_value
        readiness.updated_by = actor_id

    if status_value == "pass_to_human_review":
        await _open_human_review(
            session,
            workspace_id=workspace_id,
            actor_id=actor_id,
            artifact=artifact,
            chief_audit=audit,
            readiness=readiness,
        )

    await outbox.emit(
        session,
        event_type=f"compliance.chief_audit.{status_value}",
        workspace_id=workspace_id,
        aggregate_type="chief_audit",
        aggregate_id=audit.id,
        correlation_id=uuid.uuid4(),
        payload={"artifact_hash": artifact.artifact_hash, "blockers": blockers},
        produced_by=CHIEF_AUDITOR_WORKER_ID,
    )
    return audit


async def _open_human_review(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    artifact: FinalArtifact,
    chief_audit: ChiefAudit,
    readiness: ProductionReadiness | None,
) -> HumanReviewPackage:
    """Assemble the reviewer's package and raise the mandatory Review Gate."""
    existing = (
        await session.execute(
            select(HumanReviewPackage).where(
                HumanReviewPackage.workspace_id == workspace_id,
                HumanReviewPackage.final_artifact_id == artifact.id,
                HumanReviewPackage.artifact_hash == artifact.artifact_hash,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    job = (
        await session.execute(
            select(ProductionJob).where(
                ProductionJob.workspace_id == workspace_id,
                ProductionJob.id == artifact.production_job_id,
            )
        )
    ).scalar_one_or_none()
    compliance = (
        await session.execute(
            select(ComplianceAudit)
            .where(
                ComplianceAudit.workspace_id == workspace_id,
                ComplianceAudit.final_artifact_id == artifact.id,
                ComplianceAudit.artifact_hash == artifact.artifact_hash,
            )
            .order_by(ComplianceAudit.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    item = await session.get(ContentItem, artifact.content_item_id)
    version = await session.get(ContentVersion, artifact.content_version_id)
    if item is None or version is None:
        raise ComplianceGateError("content bound to this artifact no longer resolves")

    definition = await content_desk.ensure_desk_workflow(
        session, workspace_id=workspace_id, created_by=actor_id
    )
    _, gate = await content_desk.open_review_gate(
        session,
        workspace_id=workspace_id,
        definition=definition,
        item=item,
        version=version,
        provider=artifact.render_provider,
    )

    package = HumanReviewPackage(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        chief_audit_id=chief_audit.id,
        review_gate_id=gate.id,
        target_platform=(job.target_platform if job else None) or "unspecified",
        package_snapshot={
            "artifact_hash": artifact.artifact_hash,
            "render_provider": artifact.render_provider,
            "duration_seconds": str(artifact.duration_seconds or ""),
            "aspect_ratio": artifact.aspect_ratio,
            "script_hook": version.script_hook,
            "script_body": version.script_body,
            "script_cta": version.script_cta,
            "gate_snapshot": chief_audit.gate_snapshot,
        },
        warnings=list(chief_audit.warnings),
        required_disclosures=list(compliance.required_disclosures) if compliance else [],
        total_cost_usd=artifact.cost_usd,
        created_by=actor_id,
        test_data=artifact.test_data,
    )
    session.add(package)
    if readiness is not None:
        readiness.human_review_state = "awaiting"
        readiness.status = "awaiting_human_review"
        readiness.blocking_reasons = ["Human Review approval is outstanding"]
        readiness.updated_by = actor_id
    await session.flush()
    return package


async def create_test_compliance_pass(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    worker_id: str = "compliance-fixture",
) -> ComplianceAudit:
    artifact = await _artifact(session, workspace_id, final_artifact_id)
    media = (
        (
            await session.execute(
                select(MediaQaResult).where(
                    MediaQaResult.workspace_id == workspace_id,
                    MediaQaResult.final_artifact_id == artifact.id,
                    MediaQaResult.artifact_hash == artifact.artifact_hash,
                )
            )
        )
        .scalars()
        .first()
    )
    if media is None or media.status != "pass":
        raise ComplianceGateError("Media QA pass bound to exact artifact hash is required")
    evidence = ArtifactRightsEvidence(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        origin="test_fixture",
        rights_status="verified",
        generation_record={"mode": "test_fixture"},
        modification_lineage={"artifact_hash": artifact.artifact_hash},
        created_by=actor_id,
        test_data=True,
    )
    session.add(evidence)
    await session.flush()
    audit = ComplianceAudit(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        target_platform="test",
        compliance_worker_id=worker_id,
        input_snapshot={"mode": "test_fixture"},
        status="pass",
        risk_level="low",
        rights_status="verified",
        findings=[],
        evidence=[{"mode": "test_fixture"}],
        required_disclosures=[],
        reused_content_risk="low",
        monetization_risk="low",
        provider_state="test_fixture",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_data=True,
    )
    session.add(audit)
    await session.flush()
    return audit


async def run_test_chief_audit(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    worker_id: str = "chief-auditor-fixture",
) -> ChiefAudit:
    artifact = await _artifact(session, workspace_id, final_artifact_id)
    manifest = await create_test_manifest(session, workspace_id=workspace_id, actor_id=actor_id)
    media = (
        (
            await session.execute(
                select(MediaQaResult).where(
                    MediaQaResult.workspace_id == workspace_id,
                    MediaQaResult.final_artifact_id == artifact.id,
                    MediaQaResult.artifact_hash == artifact.artifact_hash,
                )
            )
        )
        .scalars()
        .first()
    )
    compliance = (
        (
            await session.execute(
                select(ComplianceAudit).where(
                    ComplianceAudit.workspace_id == workspace_id,
                    ComplianceAudit.final_artifact_id == artifact.id,
                    ComplianceAudit.artifact_hash == artifact.artifact_hash,
                )
            )
        )
        .scalars()
        .first()
    )
    blockers: list[str] = []
    if media is None or media.status != "pass":
        blockers.append("media_qa_missing_or_not_pass")
    if compliance is None or compliance.status != "pass":
        blockers.append("compliance_missing_or_not_pass")
    status = "pass_to_human_review" if not blockers else "blocked"
    audit = ChiefAudit(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        gate_manifest_id=manifest.id,
        chief_auditor_worker_id=worker_id,
        gate_snapshot={
            "required": DEFAULT_GATES,
            "media_qa": media.status if media else "missing",
            "compliance": compliance.status if compliance else "missing",
        },
        lineage_status="complete" if not blockers else "incomplete",
        version_integrity_status="complete" if not blockers else "incomplete",
        cost_reconciliation_status="complete" if not blockers else "incomplete",
        provider_reconciliation_status="complete" if not blockers else "incomplete",
        warnings=[],
        blockers=blockers,
        evidence=[{"mode": "test_fixture"}],
        status=status,
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_data=True,
    )
    session.add(audit)
    await session.flush()
    return audit


async def invalidate_compliance(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    compliance_audit_id: uuid.UUID,
    reason: str,
) -> ComplianceInvalidation:
    audit = (
        await session.execute(
            select(ComplianceAudit).where(
                ComplianceAudit.workspace_id == workspace_id,
                ComplianceAudit.id == compliance_audit_id,
            )
        )
    ).scalar_one_or_none()
    if audit is None:
        raise ComplianceNotFoundError("compliance audit not found")
    invalidation = ComplianceInvalidation(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        compliance_audit_id=audit.id,
        final_artifact_id=audit.final_artifact_id,
        reason=reason,
        affected_dimensions=["chief_audit", "human_review", "publication_eligibility"],
        created_by=actor_id,
    )
    session.add(invalidation)
    await session.flush()
    return invalidation


async def publication_eligibility(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    target_platform: str,
) -> ArtifactPublicationEligibility:
    artifact = await _artifact(session, workspace_id, final_artifact_id)
    chief = (
        (
            await session.execute(
                select(ChiefAudit).where(
                    ChiefAudit.workspace_id == workspace_id,
                    ChiefAudit.final_artifact_id == artifact.id,
                    ChiefAudit.artifact_hash == artifact.artifact_hash,
                )
            )
        )
        .scalars()
        .first()
    )
    blockers = ["external_publishing_disabled"]
    if chief is None or chief.status != "pass_to_human_review":
        blockers.insert(0, "chief_audit_not_passed")
    readiness = (
        await session.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact.id,
            )
        )
    ).scalar_one_or_none()
    if readiness is None or readiness.media_qa_state != "pass":
        blockers.insert(0, "media_qa_not_passed")

    # One determination per (workspace, artifact, platform) — the table is
    # uniquely constrained on exactly that and, unlike the append-only audit
    # tables, carries an update policy and a version trigger. Re-determining
    # therefore refreshes the verdict in place. Inserting unconditionally would
    # violate the constraint, so asking twice (a repeated request, or a second
    # tap on a phone) used to fail with a 500 instead of restating the answer.
    existing = (
        await session.execute(
            select(ArtifactPublicationEligibility).where(
                ArtifactPublicationEligibility.workspace_id == workspace_id,
                ArtifactPublicationEligibility.final_artifact_id == artifact.id,
                ArtifactPublicationEligibility.target_platform == target_platform,
            )
        )
    ).scalar_one_or_none()

    if existing is not None:
        existing.artifact_hash = artifact.artifact_hash
        existing.content_version_id = artifact.content_version_id
        existing.chief_audit_id = chief.id if chief else None
        existing.status = "blocked"
        existing.blocking_reasons = blockers
        existing.publication_eligible = False
        existing.updated_by = actor_id
        await session.flush()
        return existing

    row = ArtifactPublicationEligibility(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        content_version_id=artifact.content_version_id,
        target_platform=target_platform,
        chief_audit_id=chief.id if chief else None,
        status="blocked",
        blocking_reasons=blockers,
        publication_eligible=False,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(row)
    await session.flush()
    return row
