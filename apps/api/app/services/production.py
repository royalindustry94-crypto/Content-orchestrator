"""Bounded Producer and independent Media QA V1 service.

No route invokes a real provider in Founder Preview. The service persists a truthful
provider-not-configured request state and exposes test-only helpers for contract
and lineage regressions; those helpers are not mounted in the API.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content_department import ContentPackage
from app.models.production import (
    ArtifactInvalidation,
    FinalArtifact,
    MediaQaResult,
    ProductionAsset,
    ProductionJob,
    ProductionReadiness,
    ProductionRepair,
)
from app.orchestration import outbox


class ProductionNotFoundError(Exception):
    """A workspace-scoped production record was not found."""


class ProductionEligibilityError(Exception):
    """The upstream Content Package is not independently audited and eligible."""


class ProducerGateError(Exception):
    """A downstream production, QA, or readiness boundary is not satisfied."""


async def _package(
    session: AsyncSession, *, workspace_id: uuid.UUID, package_id: uuid.UUID
) -> ContentPackage:
    package = (
        await session.execute(
            select(ContentPackage).where(
                ContentPackage.workspace_id == workspace_id,
                ContentPackage.id == package_id,
            )
        )
    ).scalar_one_or_none()
    if package is None:
        raise ProductionNotFoundError("content package not found")
    return package


async def create_production_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    content_package_id: uuid.UUID,
    target_platform: str | None,
    target_format: str | None,
    target_duration_seconds: int | None,
    max_provider_calls: int,
    max_render_calls: int,
    max_cost_usd: Decimal,
    max_attempts: int,
    max_repair_cycles: int,
    timeout_seconds: int,
) -> ProductionJob:
    """Create a bounded, truthful provider-not-configured production request.

    The request is permitted only for an audited package whose Content Department
    has already granted Producer handoff eligibility. No cost or provider effect is
    created while the provider is not configured.
    """
    package = await _package(session, workspace_id=workspace_id, package_id=content_package_id)
    if package.audit_gate_status != "pass":
        raise ProductionEligibilityError(
            "content package is not eligible for Producer; all independent content audits must pass"
        )
    job = ProductionJob(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_package_id=package.id,
        content_item_id=package.content_item_id,
        content_version_id=package.content_version_id,
        producer_worker_id="producer",
        target_platform=target_platform,
        target_format=target_format,
        target_duration_seconds=target_duration_seconds,
        required_assets=list(package.package_fields.get("required_assets", [])),
        provider_plan={
            "mode": "not_configured",
            "fallbacks": [],
            "reason": "no approved media-generation, TTS, or render provider is configured",
        },
        status="blocked_provider_not_configured",
        provider_state="not_configured",
        max_provider_calls=max_provider_calls,
        max_render_calls=max_render_calls,
        max_cost_usd=max_cost_usd,
        max_total_cost_usd=max_cost_usd,
        max_attempts=max_attempts,
        max_repair_cycles=max_repair_cycles,
        timeout_seconds=timeout_seconds,
        correlation_id=uuid.uuid4(),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(job)
    await session.flush()
    await outbox.emit(
        session,
        event_type="production.requested.not_configured",
        workspace_id=workspace_id,
        aggregate_type="production_job",
        aggregate_id=job.id,
        correlation_id=job.correlation_id,
        payload={
            "content_package_id": str(package.id),
            "content_version_id": str(package.content_version_id),
            "provider_state": job.provider_state,
            "max_cost_usd": str(job.max_cost_usd),
        },
        produced_by="producer_v1",
    )
    return job


async def list_jobs(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[ProductionJob]:
    return (
        (
            await session.execute(
                select(ProductionJob)
                .where(ProductionJob.workspace_id == workspace_id)
                .order_by(ProductionJob.created_at.desc())
            )
        )
        .scalars()
        .all()
    )


async def get_job(
    session: AsyncSession, *, workspace_id: uuid.UUID, production_job_id: uuid.UUID
) -> ProductionJob:
    job = (
        await session.execute(
            select(ProductionJob).where(
                ProductionJob.workspace_id == workspace_id,
                ProductionJob.id == production_job_id,
            )
        )
    ).scalar_one_or_none()
    if job is None:
        raise ProductionNotFoundError("production job not found")
    return job


async def summary(session: AsyncSession, *, workspace_id: uuid.UUID) -> dict:
    jobs = await list_jobs(session, workspace_id=workspace_id)
    artifacts = (
        (
            await session.execute(
                select(FinalArtifact).where(FinalArtifact.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    qa_rows = (
        (
            await session.execute(
                select(MediaQaResult).where(MediaQaResult.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    readiness_rows = (
        (
            await session.execute(
                select(ProductionReadiness).where(ProductionReadiness.workspace_id == workspace_id)
            )
        )
        .scalars()
        .all()
    )
    return {
        "provider_state": "not_configured",
        "production_jobs": len(jobs),
        "active_jobs": sum(1 for row in jobs if row.status in {"queued", "running", "repairing"}),
        "final_artifacts": len(artifacts),
        "media_qa_passed": sum(1 for row in qa_rows if row.status == "pass"),
        "media_qa_blocked": sum(1 for row in qa_rows if row.status == "blocked"),
        "repair_required": sum(1 for row in qa_rows if row.status == "repair_required"),
        "compliance_ready": sum(1 for row in readiness_rows if row.status == "compliance_ready"),
        "provider_cost_usd": sum((Decimal(str(row.actual_cost_usd)) for row in jobs), Decimal("0")),
        "last_error": next((row.last_error for row in jobs if row.last_error), None),
        "real_provider_mode": False,
        "test_fixture_mode": False,
    }


async def job_detail(
    session: AsyncSession, *, workspace_id: uuid.UUID, production_job_id: uuid.UUID
) -> dict:
    job = await get_job(session, workspace_id=workspace_id, production_job_id=production_job_id)
    assets = (
        (
            await session.execute(
                select(ProductionAsset).where(
                    ProductionAsset.workspace_id == workspace_id,
                    ProductionAsset.production_job_id == job.id,
                )
            )
        )
        .scalars()
        .all()
    )
    artifacts = (
        (
            await session.execute(
                select(FinalArtifact).where(
                    FinalArtifact.workspace_id == workspace_id,
                    FinalArtifact.production_job_id == job.id,
                )
            )
        )
        .scalars()
        .all()
    )
    artifact_ids = [row.id for row in artifacts]
    qa_rows = []
    repairs = []
    readiness = []
    if artifact_ids:
        qa_rows = (
            (
                await session.execute(
                    select(MediaQaResult).where(
                        MediaQaResult.workspace_id == workspace_id,
                        MediaQaResult.final_artifact_id.in_(artifact_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
        repairs = (
            (
                await session.execute(
                    select(ProductionRepair).where(
                        ProductionRepair.workspace_id == workspace_id,
                        ProductionRepair.production_job_id == job.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        readiness = (
            (
                await session.execute(
                    select(ProductionReadiness).where(
                        ProductionReadiness.workspace_id == workspace_id,
                        ProductionReadiness.final_artifact_id.in_(artifact_ids),
                    )
                )
            )
            .scalars()
            .all()
        )
    return {
        "job": job,
        "assets": assets,
        "artifacts": artifacts,
        "media_qa": qa_rows,
        "repairs": repairs,
        "readiness": readiness,
    }


async def create_test_fixture_artifact(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    production_job_id: uuid.UUID,
    artifact_hash: str,
    producer_worker_id: str = "producer-fixture",
) -> FinalArtifact:
    """Test-only immutable artifact helper; never mounted as an API route."""
    job = await get_job(session, workspace_id=workspace_id, production_job_id=production_job_id)
    if job.test_data is not True:
        raise ProducerGateError("test fixtures are allowed only for test-marked production jobs")
    duplicate = (
        await session.execute(
            select(FinalArtifact.id).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.artifact_hash == artifact_hash,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ProducerGateError("identical final artifact hash already exists in this workspace")
    artifact = FinalArtifact(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        production_job_id=job.id,
        content_item_id=job.content_item_id,
        content_version_id=job.content_version_id,
        render_provider="test_fixture",
        artifact_hash=artifact_hash,
        storage_reference={"mode": "test_fixture", "non_public": True},
        status="ready",
        test_data=True,
        created_by=actor_id,
    )
    session.add(artifact)
    await session.flush()
    await outbox.emit(
        session,
        event_type="production.artifact.fixture_created",
        workspace_id=workspace_id,
        aggregate_type="final_artifact",
        aggregate_id=artifact.id,
        correlation_id=job.correlation_id,
        payload={"production_job_id": str(job.id), "artifact_hash": artifact_hash},
        produced_by=producer_worker_id,
    )
    return artifact


async def create_test_media_qa(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    auditor_worker_id: str,
    producer_worker_id: str,
    status: str,
) -> MediaQaResult:
    """Test-only independent QA fixture bound to the exact immutable hash."""
    artifact = (
        await session.execute(
            select(FinalArtifact).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.id == final_artifact_id,
            )
        )
    ).scalar_one_or_none()
    if artifact is None:
        raise ProductionNotFoundError("final artifact not found")
    if artifact.test_data is not True:
        raise ProducerGateError("test QA fixtures require a test-marked artifact")
    if auditor_worker_id == producer_worker_id:
        raise ProducerGateError("Producer cannot create or approve its own Media QA result")
    qa = MediaQaResult(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        auditor_worker_id=auditor_worker_id,
        status=status,
        checks_run=["fixture_hash_binding"],
        platform_check={"state": "test_fixture"},
        package_alignment={"state": "test_fixture"},
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_data=True,
    )
    session.add(qa)
    readiness = ProductionReadiness(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        content_version_id=artifact.content_version_id,
        media_qa_state=status,
        compliance_state="not_run",
        chief_audit_state="not_run",
        human_review_state="blocked",
        status="blocked",
        blocking_reasons=[
            "Compliance, Chief Auditor, and Human Review remain mandatory "
            "and are not fixture-approved"
        ],
        created_by=actor_id,
        updated_by=actor_id,
        test_data=True,
    )
    session.add(readiness)
    await session.flush()
    return qa


async def invalidate_artifact(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
    reason: str,
) -> ArtifactInvalidation:
    artifact = (
        await session.execute(
            select(FinalArtifact).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.id == final_artifact_id,
            )
        )
    ).scalar_one_or_none()
    if artifact is None:
        raise ProductionNotFoundError("final artifact not found")
    qa = (
        (
            await session.execute(
                select(MediaQaResult)
                .where(
                    MediaQaResult.workspace_id == workspace_id,
                    MediaQaResult.final_artifact_id == artifact.id,
                )
                .order_by(MediaQaResult.created_at.desc())
            )
        )
        .scalars()
        .first()
    )
    invalidation = ArtifactInvalidation(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        media_qa_result_id=qa.id if qa else None,
        reason=reason,
        affected_dimensions=["media_qa", "compliance", "chief_audit", "human_review"],
        created_by=actor_id,
    )
    session.add(invalidation)
    readiness = (
        await session.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact.id,
            )
        )
    ).scalar_one_or_none()
    if readiness is not None:
        readiness.media_qa_state = "invalidated"
        readiness.compliance_state = "invalidated"
        readiness.chief_audit_state = "invalidated"
        readiness.human_review_state = "blocked"
        readiness.status = "blocked"
        readiness.blocking_reasons = ["artifact changed or was invalidated; rerun required audits"]
        readiness.updated_by = actor_id
    await session.flush()
    return invalidation


def fixture_hash(label: str) -> str:
    """Deterministic test-only artifact hash helper."""
    return hashlib.sha256(label.encode("utf-8")).hexdigest()
