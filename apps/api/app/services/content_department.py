"""Bounded Content Department V1 service.

Browser-visible execution stops truthfully when content providers or Business Brain
context are unavailable. The only path that creates directions, versions, claims,
and audit states is isolated to tests, so preview UI cannot present synthetic work
as live output.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import ContentItem, ContentVersion
from app.models.content_department import (
    ContentAudit,
    ContentAuditInvalidation,
    ContentClaim,
    ContentDepartmentRun,
    ContentPackage,
    CreativeDirection,
    OriginalityFingerprint,
)
from app.models.enums import ContentStage, ContentStatus
from app.models.strategy import StrategyBrief
from app.orchestration.outbox import emit
from app.schemas.content_department import ContentDepartmentRunCreate
from app.services import strategy

_UNTRUSTED_INSTRUCTION = re.compile(
    r"(?i)(ignore\s+(all\s+)?previous|system\s+prompt|developer\s+message|"
    r"reveal\s+(?:secret|token|password)|bypass\s+(?:review|security)|"
    r"execute\s+this\s+instruction)"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|authorization|bearer|oauth|token|password)\s*[:=]\s*[^\s,;]+"
)
_UNSUPPORTED_CLAIM = re.compile(
    r"(?i)(will\s+go\s+viral|guaranteed\s+(?:winner|success)|"
    r"expected\s+\d+[km]?\s+views|increase\s+(?:revenue|profit)\s+by\s+\d+)"
)
_CLAIM_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_ALLOWED_AUDITORS = {"language", "fact", "brand", "originality"}
_MANDATORY_AUDITORS = ("language", "fact", "brand", "originality")


class ContentDepartmentGateError(ValueError):
    """Raised when upstream strategy or independent-audit controls deny progression."""


class ContentDepartmentNotFoundError(LookupError):
    """Raised when a workspace-scoped run, package, or direction does not exist."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _safe_text(value: str, *, field: str, maximum: int = 12_000) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must be non-empty and at most {maximum} characters")
    if _UNTRUSTED_INSTRUCTION.search(normalized):
        raise ValueError(f"{field} contains an untrusted instruction pattern")
    if _SECRET_PATTERN.search(normalized):
        raise ValueError(f"{field} contains a secret-like value")
    return normalized


def _fingerprint(value: str) -> str:
    normalized = " ".join(value.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _structure_fingerprint(*parts: str) -> str:
    normalized = "|".join(re.sub(r"[A-Za-z0-9]+", "token", part.lower()) for part in parts)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_claims(script: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for sentence in _CLAIM_SENTENCE.split(script):
        text = sentence.strip()
        if not text:
            continue
        lowered = text.lower()
        if any(char.isdigit() for char in text):
            claim_type = "NUMBER"
        elif any(marker in lowered for marker in ("will", "guarantee", "best", "more than")):
            claim_type = (
                "COMPARATIVE" if "best" in lowered or "more than" in lowered else "PRODUCT CLAIM"
            )
        else:
            continue
        claims.append(
            {
                "claim_text": text,
                "claim_type": claim_type,
                "source_required": True,
                "risk": "high" if claim_type in {"NUMBER", "COMPARATIVE"} else "medium",
            }
        )
    return claims


async def _emit_run(
    session: AsyncSession, run: ContentDepartmentRun, event_type: str, payload: dict[str, Any]
) -> None:
    await emit(
        session,
        event_type=event_type,
        workspace_id=run.workspace_id,
        aggregate_type="content_department_run",
        aggregate_id=run.id,
        correlation_id=run.correlation_id,
        trace_id=run.trace_id,
        payload=payload,
        produced_by="content-department-service",
    )


async def get_run(
    session: AsyncSession, *, workspace_id: uuid.UUID, run_id: uuid.UUID
) -> ContentDepartmentRun | None:
    return (
        await session.execute(
            select(ContentDepartmentRun).where(
                ContentDepartmentRun.id == run_id,
                ContentDepartmentRun.workspace_id == workspace_id,
            )
        )
    ).scalar_one_or_none()


async def get_package(
    session: AsyncSession, *, workspace_id: uuid.UUID, package_id: uuid.UUID
) -> ContentPackage | None:
    return (
        await session.execute(
            select(ContentPackage).where(
                ContentPackage.id == package_id,
                ContentPackage.workspace_id == workspace_id,
                ContentPackage.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def list_packages(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[ContentPackage]:
    return list(
        (
            await session.execute(
                select(ContentPackage)
                .where(
                    ContentPackage.workspace_id == workspace_id,
                    ContentPackage.deleted_at.is_(None),
                )
                .order_by(ContentPackage.created_at.desc())
            )
        ).scalars()
    )


async def _require_strategy_pass(
    session: AsyncSession, *, workspace_id: uuid.UUID, strategy_brief_id: uuid.UUID
) -> StrategyBrief:
    try:
        await strategy.writer_gate(session, workspace_id=workspace_id, brief_id=strategy_brief_id)
    except (strategy.StrategyAuditGateError, LookupError) as exc:
        raise ContentDepartmentGateError(str(exc)) from exc
    brief = await strategy.get_brief(session, workspace_id=workspace_id, brief_id=strategy_brief_id)
    if brief is None:
        raise ContentDepartmentGateError("approved strategy brief not found")
    return brief


async def create_manual_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: ContentDepartmentRunCreate,
) -> ContentDepartmentRun:
    """Persist a bounded live request without calling a content provider."""
    await _require_strategy_pass(
        session, workspace_id=workspace_id, strategy_brief_id=payload.strategy_brief_id
    )
    run = ContentDepartmentRun(
        workspace_id=workspace_id,
        strategy_brief_id=payload.strategy_brief_id,
        trigger="manual",
        status="provider_not_configured",
        provider_state="not_configured",
        business_context_state="incomplete",
        max_provider_calls=payload.max_provider_calls,
        max_tokens=payload.max_tokens,
        max_cost_usd=payload.max_cost_usd,
        max_attempts=payload.max_attempts,
        timeout_seconds=payload.timeout_seconds,
        last_error=(
            "CONTENT PROVIDER NOT CONFIGURED; BUSINESS CONTEXT INCOMPLETE; "
            "NO CREATIVE DIRECTION OR CONTENT VERSION CREATED"
        ),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(run)
    await session.flush()
    await _emit_run(
        session,
        run,
        "content_department.started",
        {
            "trigger": "manual",
            "strategy_brief_id": str(payload.strategy_brief_id),
            "limits": {
                "max_provider_calls": run.max_provider_calls,
                "max_tokens": run.max_tokens,
                "max_cost_usd": str(run.max_cost_usd),
                "max_attempts": run.max_attempts,
                "timeout_seconds": run.timeout_seconds,
            },
        },
    )
    await _emit_run(
        session,
        run,
        "content_department.provider_not_configured",
        {"detail": run.last_error},
    )
    return run


async def _latest_audit(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    package_id: uuid.UUID,
    auditor_type: str,
) -> ContentAudit | None:
    return (
        await session.execute(
            select(ContentAudit)
            .where(
                ContentAudit.workspace_id == workspace_id,
                ContentAudit.content_package_id == package_id,
                ContentAudit.auditor_type == auditor_type,
            )
            .order_by(ContentAudit.checked_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _recalculate_package_gate(session: AsyncSession, *, package: ContentPackage) -> None:
    audits = {
        kind: await _latest_audit(
            session,
            workspace_id=package.workspace_id,
            package_id=package.id,
            auditor_type=kind,
        )
        for kind in _MANDATORY_AUDITORS
    }
    states = {kind: audit.state if audit else "not_run" for kind, audit in audits.items()}
    if any(state in {"blocked", "error"} for state in states.values()):
        package.audit_gate_status = "blocked"
        package.producer_handoff_state = "blocked"
        package.status = "audited_blocked"
        return
    if all(state == "pass" for state in states.values()):
        package.audit_gate_status = "pass"
        package.producer_handoff_state = "provider_not_configured"
        package.status = "audited_ready"
        return
    package.audit_gate_status = "not_ready"
    package.producer_handoff_state = "blocked"
    package.status = "awaiting_audits"


async def record_fixture_package(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    strategy_brief_id: uuid.UUID,
    fixture: dict[str, Any],
    prior_package_id: uuid.UUID | None = None,
) -> tuple[ContentDepartmentRun, CreativeDirection, ContentPackage]:
    """Create labelled test-only lifecycle records for independent gate tests."""
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("fixture content execution is test-only")
    brief = await _require_strategy_pass(
        session, workspace_id=workspace_id, strategy_brief_id=strategy_brief_id
    )
    objective = _safe_text(str(fixture.get("objective", brief.objective)), field="objective")
    concept = _safe_text(str(fixture.get("creative_concept", objective)), field="creative concept")
    script_hook = _safe_text(
        str(fixture.get("hook", "A practical evidence-first opening.")),
        field="hook",
    )
    script_body = _safe_text(
        str(fixture.get("script", "Use approved evidence and avoid unsupported claims.")),
        field="script",
    )
    script_cta = _safe_text(
        str(fixture.get("cta", "Review the evidence before acting.")),
        field="cta",
    )
    if _UNSUPPORTED_CLAIM.search("\n".join((script_hook, script_body, script_cta))):
        raise ValueError("script contains unsupported performance or guarantee claim")

    previous: ContentPackage | None = None
    if prior_package_id is not None:
        previous = await get_package(
            session, workspace_id=workspace_id, package_id=prior_package_id
        )
        if previous is None:
            raise ContentDepartmentNotFoundError("prior content package not found")

    run = ContentDepartmentRun(
        workspace_id=workspace_id,
        strategy_brief_id=strategy_brief_id,
        trigger="test_fixture",
        status="writing",
        provider_state="fixture_test_only",
        business_context_state="complete",
        max_provider_calls=0,
        max_tokens=0,
        max_cost_usd=Decimal("0.00"),
        max_attempts=1,
        timeout_seconds=60,
        correlation_id=uuid.uuid4(),
        trace_id="content-department-test-fixture",
        test_data=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(run)
    await session.flush()

    direction = CreativeDirection(
        workspace_id=workspace_id,
        content_department_run_id=run.id,
        strategy_brief_id=strategy_brief_id,
        objective=objective,
        target_platform=fixture.get("target_platform", brief.target_platform),
        target_audience=fixture.get("target_audience", brief.target_audience),
        creative_concept=concept,
        opening_pattern=fixture.get("opening_pattern", brief.hook_direction),
        hook_direction=fixture.get("hook_direction", brief.hook_direction),
        story_structure=fixture.get("story_structure", "problem-evidence-action"),
        tone=fixture.get("tone", "clear"),
        pacing=fixture.get("pacing", "measured"),
        visual_direction=fixture.get("visual_direction", "evidence-led"),
        audio_direction=fixture.get("audio_direction", "clear narration"),
        cta_direction=fixture.get("cta_direction", brief.cta_direction),
        desired_emotion=fixture.get("desired_emotion", "confidence"),
        required_claims=list(fixture.get("required_claims", [])),
        prohibited_claims=list(fixture.get("prohibited_claims", [])),
        required_assets=list(fixture.get("required_assets", [])),
        estimated_duration=fixture.get("estimated_duration", brief.recommended_length),
        production_complexity=fixture.get("production_complexity", "low"),
        risk_notes=list(fixture.get("risk_notes", [])),
        worker_id="creative_director_fixture",
        provider="fixture_test_only",
        prompt_version="creative-director-v1-fixture",
        status="approved_for_writing",
        test_data=True,
        created_by=actor_id,
    )
    session.add(direction)
    await session.flush()

    item = ContentItem(
        workspace_id=workspace_id,
        topic=objective,
        target_length_seconds=fixture.get("target_length_seconds"),
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(item)
    await session.flush()
    version = ContentVersion(
        workspace_id=workspace_id,
        content_item_id=item.id,
        script_hook=script_hook,
        script_body=script_body,
        script_cta=script_cta,
        prompt_used="writer-v1-fixture",
        generated_by="writer_fixture",
        created_by=actor_id,
    )
    session.add(version)
    await session.flush()
    item.current_version_id = version.id

    package = ContentPackage(
        workspace_id=workspace_id,
        content_department_run_id=run.id,
        creative_direction_id=direction.id,
        strategy_brief_id=strategy_brief_id,
        content_item_id=item.id,
        content_version_id=version.id,
        prior_content_version_id=(previous.content_version_id if previous else None),
        revision_reason=(fixture.get("revision_reason") if previous else None),
        writer_worker_id="writer_fixture",
        provider="fixture_test_only",
        prompt_version="writer-v1-fixture",
        input_references={
            "strategy_brief_id": str(strategy_brief_id),
            "creative_direction_id": str(direction.id),
            "business_brain_state": "fixture_test_only",
        },
        package_fields={
            "primary_hook": script_hook,
            "script": script_body,
            "cta": script_cta,
            "title": fixture.get("title", objective),
            "description": fixture.get("description", "TEST DATA"),
        },
        status="awaiting_audits",
        audit_gate_status="not_ready",
        producer_handoff_state="blocked",
        test_data=True,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(package)
    await session.flush()

    default_claims = _extract_claims("\n".join((script_hook, script_body, script_cta)))
    claim_payloads = list(fixture.get("claims", default_claims))
    for claim in claim_payloads:
        text_value = _safe_text(str(claim["claim_text"]), field="claim text")
        session.add(
            ContentClaim(
                workspace_id=workspace_id,
                content_package_id=package.id,
                content_version_id=version.id,
                claim_text=text_value,
                claim_type=str(claim.get("claim_type", "FACT")),
                source_required=bool(claim.get("source_required", True)),
                verification_status="not_run",
                risk=str(claim.get("risk", "unknown")),
                test_data=True,
                created_by=actor_id,
                updated_by=actor_id,
            )
        )

    text_fingerprint = _fingerprint(script_body)
    hook_fingerprint = _fingerprint(script_hook)
    structure_fingerprint = _structure_fingerprint(script_hook, script_body, script_cta)
    duplicate = (
        await session.execute(
            select(OriginalityFingerprint).where(
                OriginalityFingerprint.workspace_id == workspace_id,
                OriginalityFingerprint.text_fingerprint == text_fingerprint,
            )
        )
    ).scalar_one_or_none()
    duplicate_state = "require_differentiation" if duplicate is not None else "not_run"
    comparison_set = [str(duplicate.content_version_id)] if duplicate is not None else []
    similarity_findings = (
        [{"severity": "high", "reason": "duplicate script fingerprint", "state": "blocked"}]
        if duplicate is not None
        else []
    )
    fingerprint = OriginalityFingerprint(
        workspace_id=workspace_id,
        content_package_id=package.id,
        content_version_id=version.id,
        text_fingerprint=text_fingerprint,
        hook_fingerprint=hook_fingerprint,
        structure_fingerprint=structure_fingerprint,
        semantic_reference=None,
        comparison_set=comparison_set,
        similarity_findings=similarity_findings,
        state=duplicate_state,
        test_data=True,
        created_by=actor_id,
    )
    session.add(fingerprint)
    if duplicate is not None:
        package.status = "audited_blocked"
        package.audit_gate_status = "blocked"
        package.producer_handoff_state = "blocked"

    if previous is not None:
        previous.invalidated_at = _utcnow()
        previous.audit_gate_status = "invalidated"
        previous.producer_handoff_state = "blocked"
        previous.status = "superseded"
        previous_audits = list(
            (
                await session.execute(
                    select(ContentAudit).where(
                        ContentAudit.workspace_id == workspace_id,
                        ContentAudit.content_package_id == previous.id,
                    )
                )
            ).scalars()
        )
        for audit in previous_audits:
            session.add(
                ContentAuditInvalidation(
                    workspace_id=workspace_id,
                    content_audit_id=audit.id,
                    content_package_id=previous.id,
                    content_version_id=previous.content_version_id,
                    reason="new immutable content version created",
                    affected_dimensions=list(_MANDATORY_AUDITORS),
                    created_by=actor_id,
                )
            )

    run.creative_directions_created = 1
    await _emit_run(
        session,
        run,
        "content_department.fixture_package_created",
        {"content_package_id": str(package.id), "test_data": True},
    )
    return run, direction, package


async def record_fixture_audit(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    package_id: uuid.UUID,
    auditor_type: str,
    state: str,
    findings: list[dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    blocked_reasons: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> ContentAudit:
    """Persist an independent test-only audit result and update the aggregate gate."""
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("fixture content audits are test-only")
    if auditor_type not in _ALLOWED_AUDITORS:
        raise ValueError("unsupported content auditor")
    if state not in {"pass", "pass_with_warning", "blocked", "error"}:
        raise ValueError("unsupported content audit state")
    package = await get_package(session, workspace_id=workspace_id, package_id=package_id)
    if package is None:
        raise ContentDepartmentNotFoundError("content package not found")
    direction = await session.get(CreativeDirection, package.creative_direction_id)
    if direction is None or direction.workspace_id != workspace_id:
        raise ContentDepartmentGateError("creative direction not found")
    auditor_worker_id = f"{auditor_type}_auditor_fixture"
    if auditor_worker_id in {package.writer_worker_id, direction.worker_id}:
        raise ContentDepartmentGateError(
            "creator and auditor responsibilities must remain separate"
        )

    artifact = dict(package.package_fields)
    audit = ContentAudit(
        workspace_id=workspace_id,
        content_package_id=package.id,
        content_version_id=package.content_version_id,
        auditor_type=auditor_type,
        auditor_worker_id=auditor_worker_id,
        state=state,
        artifact_snapshot=artifact,
        requirements_snapshot={
            "creative_direction_id": str(direction.id),
            "strategy_brief_id": str(package.strategy_brief_id),
            "auditor_independent": True,
        },
        findings=list(findings or []),
        warnings=list(warnings or []),
        blocked_reasons=list(blocked_reasons or []),
        evidence=list(evidence or []),
        checked_at=_utcnow(),
        cost_usd=Decimal("0.00"),
        retry_history=[],
        test_data=True,
    )
    session.add(audit)
    if auditor_type == "fact":
        claims = list(
            (
                await session.execute(
                    select(ContentClaim).where(
                        ContentClaim.workspace_id == workspace_id,
                        ContentClaim.content_package_id == package.id,
                    )
                )
            ).scalars()
        )
        verification = "verified" if state in {"pass", "pass_with_warning"} else "unverified"
        for claim in claims:
            claim.verification_status = verification
            claim.evidence_reasoning = "independent fixture audit"
            claim.updated_by = actor_id
    await session.flush()
    await _recalculate_package_gate(session, package=package)
    run = await get_run(
        session, workspace_id=workspace_id, run_id=package.content_department_run_id
    )
    if run is not None:
        if package.audit_gate_status == "pass":
            run.packages_ready += 1
        if package.audit_gate_status == "blocked":
            run.packages_blocked += 1
        await _emit_run(
            session,
            run,
            f"content_department.audit.{auditor_type}.{state}",
            {"content_package_id": str(package.id), "test_data": True},
        )
    return audit


async def producer_gate(
    session: AsyncSession, *, workspace_id: uuid.UUID, package_id: uuid.UUID
) -> dict[str, Any]:
    package = await get_package(session, workspace_id=workspace_id, package_id=package_id)
    if package is None:
        raise ContentDepartmentNotFoundError("content package not found")
    if package.audit_gate_status != "pass":
        raise ContentDepartmentGateError(
            "all mandatory independent content audits must pass before Producer eligibility"
        )
    return {
        "content_package_id": package.id,
        "eligible": False,
        "state": "provider_not_configured",
        "detail": (
            "Audited Creative Package is structurally eligible for a future Producer; "
            "no Producer provider is configured."
        ),
    }


async def package_detail(
    session: AsyncSession, *, workspace_id: uuid.UUID, package_id: uuid.UUID
) -> dict[str, Any]:
    package = await get_package(session, workspace_id=workspace_id, package_id=package_id)
    if package is None:
        raise ContentDepartmentNotFoundError("content package not found")
    direction = await session.get(CreativeDirection, package.creative_direction_id)
    if direction is None or direction.workspace_id != workspace_id:
        raise ContentDepartmentGateError("creative direction not found")
    claims = list(
        (
            await session.execute(
                select(ContentClaim).where(
                    ContentClaim.workspace_id == workspace_id,
                    ContentClaim.content_package_id == package.id,
                )
            )
        ).scalars()
    )
    audits = list(
        (
            await session.execute(
                select(ContentAudit)
                .where(
                    ContentAudit.workspace_id == workspace_id,
                    ContentAudit.content_package_id == package.id,
                )
                .order_by(ContentAudit.checked_at.desc())
            )
        ).scalars()
    )
    originality = (
        await session.execute(
            select(OriginalityFingerprint).where(
                OriginalityFingerprint.workspace_id == workspace_id,
                OriginalityFingerprint.content_package_id == package.id,
            )
        )
    ).scalar_one_or_none()
    invalidation_count = (
        await session.execute(
            select(func.count(ContentAuditInvalidation.id)).where(
                ContentAuditInvalidation.workspace_id == workspace_id,
                ContentAuditInvalidation.content_package_id == package.id,
            )
        )
    ).scalar_one()
    return {
        "package": package,
        "direction": direction,
        "claims": claims,
        "audits": audits,
        "originality": originality,
        "invalidation_count": invalidation_count,
    }


async def summary(session: AsyncSession, *, workspace_id: uuid.UUID) -> dict[str, Any]:
    runs = list(
        (
            await session.execute(
                select(ContentDepartmentRun)
                .where(ContentDepartmentRun.workspace_id == workspace_id)
                .order_by(ContentDepartmentRun.created_at.desc())
            )
        ).scalars()
    )
    current = next((run for run in runs if run.status in {"queued", "writing", "auditing"}), None)
    last = runs[0] if runs else None
    package_counts = (
        await session.execute(
            select(
                func.count(ContentPackage.id),
                func.count(ContentPackage.id).filter(ContentPackage.audit_gate_status == "pass"),
                func.count(ContentPackage.id).filter(ContentPackage.audit_gate_status == "blocked"),
                func.count(ContentPackage.id).filter(
                    ContentPackage.audit_gate_status.not_in(("pass", "blocked"))
                ),
            ).where(
                ContentPackage.workspace_id == workspace_id,
                ContentPackage.deleted_at.is_(None),
            )
        )
    ).one()
    unverified = (
        await session.execute(
            select(func.count(ContentClaim.id)).where(
                ContentClaim.workspace_id == workspace_id,
                ContentClaim.verification_status.not_in(("verified", "not_applicable")),
            )
        )
    ).scalar_one()
    directions = (
        await session.execute(
            select(func.count(CreativeDirection.id)).where(
                CreativeDirection.workspace_id == workspace_id
            )
        )
    ).scalar_one()
    return {
        "provider_state": "not_configured",
        "status": last.status if last else "not_configured",
        "current_run": current,
        "last_run": last,
        "creative_directions": directions,
        "packages_ready": package_counts[1],
        "packages_blocked": package_counts[2],
        "packages_in_progress": package_counts[3],
        "claims_unverified": unverified,
        "cost_today_usd": Decimal("0.00"),
        "last_error": last.last_error if last else "CONTENT PROVIDER NOT CONFIGURED",
        "schedule_enabled": False,
        "business_context_state": "incomplete",
        "performance_data_state": "no_data",
    }
