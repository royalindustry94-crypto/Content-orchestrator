"""Bounded Producer and independent Media QA V1 service.

Rendering goes through the configured pipeline provider; without one the
service persists a truthful provider-not-configured request and creates no
artifact. Media QA is a separate independent step that inspects the stored
artifact's lineage and platform fitness, and it never trusts the Producer that
rendered it. Compliance, Chief Auditor, and Human Review all remain mandatory
after a Media QA pass.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentVersion
from app.models.content_department import ContentPackage
from app.models.delivery import Asset
from app.models.enums import AssetSource, AssetStatus, AssetType
from app.models.production import (
    ArtifactInvalidation,
    FinalArtifact,
    MediaQaResult,
    ProductionAsset,
    ProductionJob,
    ProductionReadiness,
    ProductionRepair,
)
from app.models.strategy import StrategyBrief
from app.orchestration import outbox
from app.providers import ProductionRequest, ProviderExecutionError, get_pipeline_provider

PRODUCER_WORKER_ID = "producer"
MEDIA_QA_WORKER_ID = "media_qa_auditor"

# Platform delivery constraints Media QA checks the rendered artifact against.
# Values are conservative published limits for vertical short-form surfaces;
# an unknown platform is checked for internal consistency only, never waved
# through as compliant.
PLATFORM_CONSTRAINTS: dict[str, dict[str, object]] = {
    "youtube_shorts": {"max_duration_seconds": 180, "aspect_ratio": "9:16"},
    "tiktok": {"max_duration_seconds": 600, "aspect_ratio": "9:16"},
    "instagram_reels": {"max_duration_seconds": 180, "aspect_ratio": "9:16"},
}


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
    """Create a bounded production request and render it through the provider.

    The request is permitted only for an audited package whose Content Department
    has already granted Producer handoff eligibility. Without a configured
    provider no artifact is created and nothing is spent.
    """
    provider = get_pipeline_provider()
    package = await _package(session, workspace_id=workspace_id, package_id=content_package_id)
    if package.audit_gate_status != "pass":
        raise ProductionEligibilityError(
            "content package is not eligible for Producer; all independent content audits must pass"
        )
    # Fall back to the delivery target the audited strategy already chose rather
    # than making the operator retype it. Media QA checks the artifact against
    # this platform's constraints and fails closed on an unknown one, so an
    # omitted platform would otherwise block a correctly produced artifact.
    if target_platform is None or target_format is None:
        brief = (
            await session.execute(
                select(StrategyBrief).where(
                    StrategyBrief.workspace_id == workspace_id,
                    StrategyBrief.id == package.strategy_brief_id,
                )
            )
        ).scalar_one_or_none()
        if brief is not None:
            target_platform = target_platform or brief.target_platform
            target_format = target_format or brief.content_format
    configured = provider.is_configured
    job = ProductionJob(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        content_package_id=package.id,
        content_item_id=package.content_item_id,
        content_version_id=package.content_version_id,
        producer_worker_id=PRODUCER_WORKER_ID,
        target_platform=target_platform,
        target_format=target_format,
        target_duration_seconds=target_duration_seconds,
        required_assets=list(package.package_fields.get("required_assets", [])),
        provider_plan=(
            {"mode": provider.name, "fallbacks": [], "reason": "configured render provider"}
            if configured
            else {
                "mode": "not_configured",
                "fallbacks": [],
                "reason": "no approved media-generation, TTS, or render provider is configured",
            }
        ),
        status="running" if configured else "blocked_provider_not_configured",
        provider_state=provider.state_label,
        max_provider_calls=max_provider_calls,
        max_render_calls=max_render_calls,
        max_cost_usd=max_cost_usd,
        max_total_cost_usd=max_cost_usd,
        max_attempts=max_attempts,
        max_repair_cycles=max_repair_cycles,
        timeout_seconds=timeout_seconds,
        correlation_id=uuid.uuid4(),
        started_at=datetime.now(UTC),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(job)
    await session.flush()
    if not configured:
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

    version = await session.get(ContentVersion, package.content_version_id)
    if version is None or version.workspace_id != workspace_id:
        raise ProductionNotFoundError("content version bound to this package not found")
    try:
        result = await provider.production(
            ProductionRequest(
                workspace_id=workspace_id,
                script_hook=version.script_hook or "",
                script_body=version.script_body or "",
                script_cta=version.script_cta or "",
                target_platform=target_platform,
                target_format=target_format,
                target_duration_seconds=target_duration_seconds,
            )
        )
    except Exception as exc:  # a failed render is a failed job, never an unconfigured one
        job.status = "failed"
        job.last_error = f"production provider '{provider.name}' failed: {exc}"
        job.completed_at = datetime.now(UTC)
        await outbox.emit(
            session,
            event_type="production.failed",
            workspace_id=workspace_id,
            aggregate_type="production_job",
            aggregate_id=job.id,
            correlation_id=job.correlation_id,
            payload={"reason": job.last_error},
            produced_by="producer_v1",
        )
        return job

    duplicate = (
        await session.execute(
            select(FinalArtifact.id).where(
                FinalArtifact.workspace_id == workspace_id,
                FinalArtifact.artifact_hash == result.artifact_hash,
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        job.status = "duplicate"
        job.last_error = "an identical final artifact already exists in this workspace"
        job.completed_at = datetime.now(UTC)
        return job

    render_asset_id: uuid.UUID | None = None
    for draft in result.assets:
        asset = Asset(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            content_item_id=package.content_item_id,
            content_version_id=package.content_version_id,
            type=AssetType(draft.asset_type),
            source=AssetSource.AI_GENERATED,
            status=AssetStatus.READY,
            provider_metadata={
                "provider": provider.name,
                "model_version": draft.model_version,
                **draft.generation_settings,
            },
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(asset)
        await session.flush()
        session.add(
            ProductionAsset(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                production_job_id=job.id,
                asset_id=asset.id,
                content_item_id=package.content_item_id,
                content_version_id=package.content_version_id,
                asset_type=draft.asset_type,
                provider=provider.name,
                source_inputs={"content_version_id": str(package.content_version_id)},
                generation_settings=dict(draft.generation_settings),
                model_version=draft.model_version,
                duration_seconds=draft.duration_seconds,
                dimensions=dict(draft.dimensions),
                cost_usd=draft.cost_usd,
                status="ready",
                created_by=actor_id,
            )
        )
        if draft.asset_type == AssetType.RENDER.value:
            render_asset_id = asset.id

    artifact = FinalArtifact(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        production_job_id=job.id,
        content_item_id=package.content_item_id,
        content_version_id=package.content_version_id,
        render_asset_id=render_asset_id,
        render_provider=provider.name,
        artifact_hash=result.artifact_hash,
        storage_reference=dict(result.storage_reference),
        duration_seconds=result.duration_seconds,
        resolution=dict(result.resolution),
        aspect_ratio=result.aspect_ratio,
        container=result.container,
        codec=result.codec,
        cost_usd=result.usage.cost_usd,
        status="ready",
        created_by=actor_id,
    )
    session.add(artifact)
    await session.flush()

    job.status = "awaiting_media_qa"
    job.render_calls_used = 1
    job.provider_calls_used = result.usage.calls
    job.actual_cost_usd = result.usage.cost_usd
    job.completed_at = datetime.now(UTC)
    if Decimal(str(job.actual_cost_usd)) > Decimal(str(job.max_total_cost_usd)):
        raise ProviderExecutionError(
            "production provider reported cost above the job's persisted ceiling"
        )
    await outbox.emit(
        session,
        event_type="production.artifact_created",
        workspace_id=workspace_id,
        aggregate_type="production_job",
        aggregate_id=job.id,
        correlation_id=job.correlation_id,
        payload={
            "final_artifact_id": str(artifact.id),
            "artifact_hash": artifact.artifact_hash,
            "provider": provider.name,
        },
        produced_by="producer_v1",
    )
    return job


async def run_media_qa(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    final_artifact_id: uuid.UUID,
) -> MediaQaResult:
    """Independently check a rendered artifact's lineage and platform fitness.

    Media QA reads persisted state only and is bound to the exact artifact hash,
    so an artifact that changes afterwards cannot inherit this result.
    """
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
    existing = (
        await session.execute(
            select(MediaQaResult).where(
                MediaQaResult.workspace_id == workspace_id,
                MediaQaResult.final_artifact_id == artifact.id,
                MediaQaResult.artifact_hash == artifact.artifact_hash,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    job = await get_job(
        session, workspace_id=workspace_id, production_job_id=artifact.production_job_id
    )
    if job.producer_worker_id == MEDIA_QA_WORKER_ID:
        raise ProducerGateError("Producer cannot create or approve its own Media QA result")

    assets = list(
        (
            await session.execute(
                select(ProductionAsset).where(
                    ProductionAsset.workspace_id == workspace_id,
                    ProductionAsset.production_job_id == job.id,
                )
            )
        ).scalars()
    )
    version = await session.get(ContentVersion, artifact.content_version_id)

    checks_run = [
        "lineage_binding",
        "artifact_readiness",
        "component_presence",
        "platform_constraints",
        "script_alignment",
        "invalidation_check",
    ]
    visual_findings: list[dict[str, str]] = []
    audio_findings: list[dict[str, str]] = []
    subtitle_findings: list[dict[str, str]] = []
    blocking: list[str] = []

    if artifact.content_version_id != job.content_version_id:
        blocking.append("artifact is not bound to the content version its job was created for")
    if artifact.status != "ready":
        blocking.append(f"artifact status is '{artifact.status}' rather than ready")

    asset_types = {asset.asset_type for asset in assets}
    if AssetType.RENDER.value not in asset_types:
        blocking.append("no rendered component is attached to this artifact")
        visual_findings.append({"severity": "high", "reason": "missing render component"})
    if AssetType.AUDIO.value not in asset_types:
        blocking.append("no audio component is attached to this artifact")
        audio_findings.append({"severity": "high", "reason": "missing audio component"})
    if AssetType.VISUAL.value not in asset_types:
        subtitle_findings.append({"severity": "medium", "reason": "no caption component recorded"})

    platform = job.target_platform or ""
    constraints = PLATFORM_CONSTRAINTS.get(platform)
    platform_check: dict[str, object] = {"platform": platform or "unspecified"}
    if constraints is None:
        platform_check["state"] = "unknown_platform"
        named = platform or "unspecified"
        blocking.append(f"no published delivery constraints are known for platform '{named}'")
    else:
        platform_check["state"] = "checked"
        max_duration = int(constraints["max_duration_seconds"])
        duration = Decimal(str(artifact.duration_seconds or 0))
        platform_check["max_duration_seconds"] = max_duration
        platform_check["duration_seconds"] = str(duration)
        if duration <= 0:
            blocking.append("artifact duration is missing")
        elif duration > max_duration:
            blocking.append(
                f"artifact runs {duration}s, above the {max_duration}s limit for {platform}"
            )
        platform_check["required_aspect_ratio"] = constraints["aspect_ratio"]
        platform_check["aspect_ratio"] = artifact.aspect_ratio
        if artifact.aspect_ratio != constraints["aspect_ratio"]:
            blocking.append(
                f"artifact aspect ratio {artifact.aspect_ratio} does not match "
                f"{constraints['aspect_ratio']} required by {platform}"
            )
            visual_findings.append({"severity": "high", "reason": "aspect ratio mismatch"})

    script_alignment: dict[str, object] = {}
    if version is None or version.workspace_id != workspace_id:
        blocking.append("the content version this artifact renders no longer resolves")
    else:
        script_alignment = {
            "content_version_id": str(version.id),
            "script_present": bool((version.script_body or "").strip()),
        }
        if not (version.script_body or "").strip():
            blocking.append("the bound content version has no script body")

    invalidated = (
        await session.execute(
            select(ArtifactInvalidation.id).where(
                ArtifactInvalidation.workspace_id == workspace_id,
                ArtifactInvalidation.final_artifact_id == artifact.id,
            )
        )
    ).first()
    if invalidated is not None:
        blocking.append("this artifact has a recorded invalidation")

    status_value = "blocked" if blocking else "pass"
    qa = MediaQaResult(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        final_artifact_id=artifact.id,
        artifact_hash=artifact.artifact_hash,
        auditor_worker_id=MEDIA_QA_WORKER_ID,
        status=status_value,
        checks_run=checks_run,
        visual_findings=visual_findings,
        audio_findings=audio_findings,
        subtitle_findings=subtitle_findings,
        script_alignment=script_alignment,
        platform_check=platform_check,
        package_alignment={
            "content_package_id": str(job.content_package_id),
            "required_assets": list(job.required_assets or []),
            "components_present": sorted(asset_types),
        },
        evidence=[{"source": "persisted_artifact_metadata", "artifact_id": str(artifact.id)}],
        recommended_repair=(
            [{"operation": "re_render", "reason": reason} for reason in blocking]
            if blocking
            else []
        ),
        cost_usd=Decimal("0.00"),
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        test_data=artifact.test_data,
    )
    session.add(qa)
    await _upsert_readiness(
        session,
        workspace_id=workspace_id,
        actor_id=actor_id,
        artifact=artifact,
        media_qa_state=status_value,
    )
    job.status = "media_qa_passed" if status_value == "pass" else "media_qa_blocked"
    await session.flush()
    await outbox.emit(
        session,
        event_type=f"production.media_qa.{status_value}",
        workspace_id=workspace_id,
        aggregate_type="final_artifact",
        aggregate_id=artifact.id,
        correlation_id=job.correlation_id,
        payload={"artifact_hash": artifact.artifact_hash, "blocking_reasons": blocking},
        produced_by=MEDIA_QA_WORKER_ID,
    )
    return qa


async def _upsert_readiness(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    artifact: FinalArtifact,
    media_qa_state: str,
) -> ProductionReadiness:
    """Record readiness with the downstream gates still explicitly outstanding."""
    readiness = (
        await session.execute(
            select(ProductionReadiness).where(
                ProductionReadiness.workspace_id == workspace_id,
                ProductionReadiness.final_artifact_id == artifact.id,
            )
        )
    ).scalar_one_or_none()
    blocking = [
        "Compliance, Chief Auditor, and Human Review remain mandatory and are not yet satisfied"
    ]
    if media_qa_state != "pass":
        blocking.insert(0, "Media QA did not pass")
    if readiness is None:
        readiness = ProductionReadiness(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            final_artifact_id=artifact.id,
            content_version_id=artifact.content_version_id,
            media_qa_state=media_qa_state,
            compliance_state="not_run",
            chief_audit_state="not_run",
            human_review_state="blocked",
            status="blocked",
            blocking_reasons=blocking,
            total_cost_usd=artifact.cost_usd,
            created_by=actor_id,
            updated_by=actor_id,
            test_data=artifact.test_data,
        )
        session.add(readiness)
    else:
        readiness.media_qa_state = media_qa_state
        readiness.blocking_reasons = blocking
        readiness.status = "blocked"
        readiness.updated_by = actor_id
    await session.flush()
    return readiness


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
    provider = get_pipeline_provider()
    return {
        "provider_state": provider.state_label,
        "production_jobs": len(jobs),
        "active_jobs": sum(1 for row in jobs if row.status in {"queued", "running", "repairing"}),
        "final_artifacts": len(artifacts),
        "media_qa_passed": sum(1 for row in qa_rows if row.status == "pass"),
        "media_qa_blocked": sum(1 for row in qa_rows if row.status == "blocked"),
        "repair_required": sum(1 for row in qa_rows if row.status == "repair_required"),
        "compliance_ready": sum(1 for row in readiness_rows if row.status == "compliance_ready"),
        "provider_cost_usd": sum((Decimal(str(row.actual_cost_usd)) for row in jobs), Decimal("0")),
        "last_error": next((row.last_error for row in jobs if row.last_error), None),
        # A simulated render is never a real provider effect, so this stays
        # false until PROVIDER-001 activates a live vendor.
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
