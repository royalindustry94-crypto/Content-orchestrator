"""Bounded Content Department V1 service.

Execution stops truthfully when no content provider is configured. When one is,
the Creative Director and Writer outputs are persisted as immutable content
versions and then handed to four independent auditors — language, fact, brand,
and originality — which inspect the stored artifact rather than trusting the
producer that wrote it. Producer handoff requires all four to pass.
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
from app.providers import (
    ContentRequest,
    CreativeDirectionDraft,
    ProviderExecutionError,
    ScriptDraft,
    get_pipeline_provider,
)
from app.schemas.content_department import ContentDepartmentRunCreate
from app.services import research, strategy

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
    """Persist a bounded request and execute it through the configured provider.

    Without a configured provider no creative direction and no content version
    are created, and nothing is spent.
    """
    provider = get_pipeline_provider()
    brief = await _require_strategy_pass(
        session, workspace_id=workspace_id, strategy_brief_id=payload.strategy_brief_id
    )
    run = ContentDepartmentRun(
        workspace_id=workspace_id,
        strategy_brief_id=payload.strategy_brief_id,
        trigger="manual",
        status="writing" if provider.is_configured else "provider_not_configured",
        provider_state=provider.state_label,
        business_context_state="complete" if provider.is_configured else "incomplete",
        max_provider_calls=payload.max_provider_calls,
        max_tokens=payload.max_tokens,
        max_cost_usd=payload.max_cost_usd,
        max_attempts=payload.max_attempts,
        timeout_seconds=payload.timeout_seconds,
        correlation_id=uuid.uuid4(),
        last_error=(
            None
            if provider.is_configured
            else (
                "CONTENT PROVIDER NOT CONFIGURED; BUSINESS CONTEXT INCOMPLETE; "
                "NO CREATIVE DIRECTION OR CONTENT VERSION CREATED"
            )
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
            "provider": provider.name,
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
    if not provider.is_configured:
        await _emit_run(
            session,
            run,
            "content_department.provider_not_configured",
            {"detail": run.last_error},
        )
        return run

    try:
        result = await provider.content(
            ContentRequest(
                workspace_id=workspace_id,
                objective=brief.objective,
                creative_angle=brief.creative_angle,
                core_message=brief.core_message,
                hook_direction=brief.hook_direction,
                cta_direction=brief.cta_direction,
                target_platform=brief.target_platform,
                target_audience=brief.target_audience,
                recommended_length=brief.recommended_length,
            )
        )
    except Exception as exc:  # a failed provider call is a failed run, not an unconfigured one
        run.status = "failed"
        run.last_error = f"content provider '{provider.name}' failed: {exc}"
        await _emit_run(session, run, "content_department.failed", {"reason": run.last_error})
        return run

    _, package = await _persist_content_package(
        session,
        run=run,
        actor_id=actor_id,
        brief=brief,
        objective=brief.objective,
        direction_draft=result.direction,
        script=result.script,
        worker_suffix=provider.name,
        prior_package_id=payload.prior_content_package_id,
        revision_reason=(
            "revision requested by operator" if payload.prior_content_package_id else None
        ),
    )
    run.status = "awaiting_audits"
    run.provider_calls_used = result.usage.calls
    run.tokens_used = result.usage.tokens
    run.actual_cost_usd = result.usage.cost_usd
    if Decimal(str(run.actual_cost_usd)) > Decimal(str(run.max_cost_usd)):
        raise ProviderExecutionError(
            "content provider reported cost above the run's persisted ceiling"
        )
    await _emit_run(
        session,
        run,
        "content_department.package_created",
        {"content_package_id": str(package.id), "provider": provider.name},
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
        package.producer_handoff_state = (
            "eligible" if get_pipeline_provider().is_configured else "provider_not_configured"
        )
        package.status = "audited_ready"
        return
    package.audit_gate_status = "not_ready"
    package.producer_handoff_state = "blocked"
    package.status = "awaiting_audits"


def _audit_language(
    *, script_text: str, package: ContentPackage
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Inspect the stored script for unsafe or unusable language."""
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocked: list[str] = []
    if _UNTRUSTED_INSTRUCTION.search(script_text):
        blocked.append("Script contains an untrusted instruction pattern.")
    if _SECRET_PATTERN.search(script_text):
        blocked.append("Script contains a secret-like value.")
    if _UNSUPPORTED_CLAIM.search(script_text):
        blocked.append("Script contains an unsupported performance or guarantee claim.")
    for field_name in ("primary_hook", "script", "cta"):
        if not str(package.package_fields.get(field_name, "")).strip():
            blocked.append(f"Package field '{field_name}' is empty.")
    findings.append(
        {
            "check": "prompt_injection",
            "result": "clean" if not _UNTRUSTED_INSTRUCTION.search(script_text) else "flagged",
        }
    )
    findings.append(
        {
            "check": "secret_disclosure",
            "result": "clean" if not _SECRET_PATTERN.search(script_text) else "flagged",
        }
    )
    return findings, warnings, blocked


async def _audit_fact(
    session: AsyncSession,
    *,
    package: ContentPackage,
    claims: list[ContentClaim],
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Check that every claim is traceable to audited upstream evidence.

    This auditor verifies *traceability*, not truth. Establishing the truth of a
    quantitative or comparative assertion needs an external verification
    provider, so those claim types are blocked rather than assumed correct.
    """
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocked: list[str] = []

    opportunity_ids = await strategy.brief_opportunity_ids(
        session, workspace_id=package.workspace_id, brief_id=package.strategy_brief_id
    )
    if not opportunity_ids:
        blocked.append("No audited research evidence is linked to this content package.")
    for opportunity_id in opportunity_ids:
        audit = await research.latest_audit(
            session, workspace_id=package.workspace_id, opportunity_id=opportunity_id
        )
        if audit is None or audit.state != "pass":
            blocked.append("Every linked research opportunity must hold a Research Auditor pass.")
            break
        findings.append(
            {
                "opportunity_id": str(opportunity_id),
                "research_audit_state": audit.state,
                "evidence_traceability": "pass",
            }
        )

    for claim in claims:
        if not claim.source_required:
            continue
        if claim.claim_type in {"NUMBER", "COMPARATIVE"}:
            blocked.append(
                f"Claim '{claim.claim_text[:80]}' asserts a quantity or comparison that "
                "the linked evidence does not establish; an external verification "
                "provider is required."
            )
        else:
            warnings.append(
                f"Claim '{claim.claim_text[:80]}' rests on upstream evidence rather than "
                "on direct verification."
            )
    return findings, warnings, blocked


def _audit_brand(
    *, script_text: str, direction: CreativeDirection
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Check the script against the creative direction's literal constraints."""
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocked: list[str] = []
    lowered = script_text.lower()
    for phrase in direction.prohibited_claims or []:
        if str(phrase).strip().lower() in lowered:
            blocked.append(f"Script contains prohibited phrase '{phrase}'.")
    for phrase in direction.required_claims or []:
        if str(phrase).strip().lower() not in lowered:
            blocked.append(f"Script omits required phrase '{phrase}'.")
    findings.append(
        {
            "check": "prohibited_phrases",
            "result": f"{len(direction.prohibited_claims or [])} checked",
        }
    )
    findings.append(
        {"check": "required_phrases", "result": f"{len(direction.required_claims or [])} checked"}
    )
    return findings, warnings, blocked


def _audit_originality(
    *, fingerprint: OriginalityFingerprint | None
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Check the stored similarity fingerprint for reuse of existing content."""
    findings: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocked: list[str] = []
    if fingerprint is None:
        blocked.append("No originality fingerprint was recorded for this content version.")
        return findings, warnings, blocked
    if fingerprint.state in {"require_differentiation", "duplicate", "blocked"}:
        blocked.append("An existing content version in this workspace shares this script.")
    findings.append({"check": "text_fingerprint", "result": fingerprint.state})
    findings.append(
        {"check": "comparison_set_size", "result": str(len(fingerprint.comparison_set or []))}
    )
    return findings, warnings, blocked


def _audit_state(warnings: list[str], blocked: list[str]) -> str:
    if blocked:
        return "blocked"
    return "pass_with_warning" if warnings else "pass"


async def run_content_audits(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    package_id: uuid.UUID,
) -> list[ContentAudit]:
    """Run all four mandatory independent auditors against a stored package.

    The auditors read persisted state only. They never consult the provider
    that produced the package, and they run identically whichever provider that
    was, which is what makes the Producer handoff gate meaningful.
    """
    package = await get_package(session, workspace_id=workspace_id, package_id=package_id)
    if package is None:
        raise ContentDepartmentNotFoundError("content package not found")
    direction = await session.get(CreativeDirection, package.creative_direction_id)
    if direction is None or direction.workspace_id != workspace_id:
        raise ContentDepartmentGateError("creative direction not found")
    if package.invalidated_at is not None:
        raise ContentDepartmentGateError("content package has been superseded")

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
    fingerprint = (
        await session.execute(
            select(OriginalityFingerprint).where(
                OriginalityFingerprint.workspace_id == workspace_id,
                OriginalityFingerprint.content_package_id == package.id,
            )
        )
    ).scalar_one_or_none()
    script_text = "\n".join(
        str(package.package_fields.get(field_name, ""))
        for field_name in ("primary_hook", "script", "cta")
    )

    results: dict[str, tuple[list[dict[str, Any]], list[str], list[str]]] = {
        "language": _audit_language(script_text=script_text, package=package),
        "fact": await _audit_fact(session, package=package, claims=claims),
        "brand": _audit_brand(script_text=script_text, direction=direction),
        "originality": _audit_originality(fingerprint=fingerprint),
    }

    audits: list[ContentAudit] = []
    for auditor_type in _MANDATORY_AUDITORS:
        findings, warnings, blocked = results[auditor_type]
        audits.append(
            await _persist_content_audit(
                session,
                package=package,
                direction=direction,
                actor_id=actor_id,
                auditor_type=auditor_type,
                auditor_worker_id=f"{auditor_type}_auditor",
                state=_audit_state(warnings, blocked),
                findings=findings,
                warnings=warnings,
                blocked_reasons=blocked,
                evidence=[{"source": "persisted_content_package", "package_id": str(package.id)}],
            )
        )

    await session.flush()
    await _recalculate_package_gate(session, package=package)
    run = await get_run(
        session, workspace_id=workspace_id, run_id=package.content_department_run_id
    )
    if run is not None:
        if package.audit_gate_status == "pass":
            run.packages_ready += 1
            run.status = "succeeded"
        if package.audit_gate_status == "blocked":
            run.packages_blocked += 1
            run.status = "blocked"
        await _emit_run(
            session,
            run,
            f"content_department.audits.{package.audit_gate_status}",
            {
                "content_package_id": str(package.id),
                "states": {audit.auditor_type: audit.state for audit in audits},
            },
        )
    return audits


async def _persist_content_audit(
    session: AsyncSession,
    *,
    package: ContentPackage,
    direction: CreativeDirection,
    actor_id: uuid.UUID,
    auditor_type: str,
    auditor_worker_id: str,
    state: str,
    findings: list[dict[str, Any]],
    warnings: list[str],
    blocked_reasons: list[str],
    evidence: list[dict[str, Any]],
) -> ContentAudit:
    """Write one audit record, refusing any auditor that also produced the work."""
    if auditor_worker_id in {package.writer_worker_id, direction.worker_id}:
        raise ContentDepartmentGateError(
            "creator and auditor responsibilities must remain separate"
        )
    audit = ContentAudit(
        workspace_id=package.workspace_id,
        content_package_id=package.id,
        content_version_id=package.content_version_id,
        auditor_type=auditor_type,
        auditor_worker_id=auditor_worker_id,
        state=state,
        artifact_snapshot=dict(package.package_fields),
        requirements_snapshot={
            "creative_direction_id": str(direction.id),
            "strategy_brief_id": str(package.strategy_brief_id),
            "auditor_independent": True,
        },
        findings=list(findings),
        warnings=list(warnings),
        blocked_reasons=list(blocked_reasons),
        evidence=list(evidence),
        checked_at=_utcnow(),
        cost_usd=Decimal("0.00"),
        retry_history=[],
        test_data=package.test_data,
    )
    session.add(audit)
    if auditor_type == "fact":
        verification = "verified" if state in {"pass", "pass_with_warning"} else "unverified"
        claims = list(
            (
                await session.execute(
                    select(ContentClaim).where(
                        ContentClaim.workspace_id == package.workspace_id,
                        ContentClaim.content_package_id == package.id,
                    )
                )
            ).scalars()
        )
        for claim in claims:
            claim.verification_status = verification
            claim.evidence_reasoning = "independent evidence-traceability audit"
            claim.updated_by = actor_id
    return audit


async def _persist_content_package(
    session: AsyncSession,
    *,
    run: ContentDepartmentRun,
    actor_id: uuid.UUID,
    brief: StrategyBrief,
    objective: str,
    direction_draft: CreativeDirectionDraft,
    script: ScriptDraft,
    worker_suffix: str,
    prior_package_id: uuid.UUID | None = None,
    target_length_seconds: int | None = None,
    revision_reason: str | None = None,
    claim_overrides: list[dict[str, Any]] | None = None,
) -> tuple[CreativeDirection, ContentPackage]:
    """Persist a creative direction, immutable content version, and package.

    Shared by the provider path and the test fixture path. Writer and auditor
    worker identities are derived here so the two can never collide, which is
    what keeps the independence check in ``record_content_audit`` meaningful.
    """
    workspace_id = run.workspace_id
    test_data = run.test_data
    objective = _safe_text(objective, field="objective")
    concept = _safe_text(direction_draft.creative_concept, field="creative concept")
    script_hook = _safe_text(script.hook, field="hook")
    script_body = _safe_text(script.body, field="script")
    script_cta = _safe_text(script.cta, field="cta")
    if _UNSUPPORTED_CLAIM.search("\n".join((script_hook, script_body, script_cta))):
        raise ValueError("script contains unsupported performance or guarantee claim")

    previous: ContentPackage | None = None
    if prior_package_id is not None:
        previous = await get_package(
            session, workspace_id=workspace_id, package_id=prior_package_id
        )
        if previous is None:
            raise ContentDepartmentNotFoundError("prior content package not found")

    direction = CreativeDirection(
        workspace_id=workspace_id,
        content_department_run_id=run.id,
        strategy_brief_id=brief.id,
        objective=objective,
        target_platform=brief.target_platform,
        target_audience=brief.target_audience,
        creative_concept=concept,
        opening_pattern=direction_draft.opening_pattern,
        hook_direction=brief.hook_direction,
        story_structure=direction_draft.story_structure,
        tone=direction_draft.tone,
        pacing=direction_draft.pacing,
        visual_direction=direction_draft.visual_direction,
        audio_direction=direction_draft.audio_direction,
        cta_direction=brief.cta_direction,
        desired_emotion=direction_draft.desired_emotion,
        required_claims=list(direction_draft.required_claims),
        prohibited_claims=list(direction_draft.prohibited_claims),
        required_assets=list(direction_draft.required_assets),
        estimated_duration=direction_draft.estimated_duration,
        production_complexity=direction_draft.production_complexity,
        risk_notes=list(direction_draft.risk_notes),
        worker_id=f"creative_director_{worker_suffix}",
        provider=run.provider_state,
        prompt_version=f"creative-director-v1-{worker_suffix}",
        status="approved_for_writing",
        test_data=test_data,
        created_by=actor_id,
    )
    session.add(direction)
    await session.flush()

    item = ContentItem(
        workspace_id=workspace_id,
        topic=objective,
        target_length_seconds=target_length_seconds,
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
        prompt_used=f"writer-v1-{worker_suffix}",
        generated_by=f"writer_{worker_suffix}",
        created_by=actor_id,
    )
    session.add(version)
    await session.flush()
    item.current_version_id = version.id

    package = ContentPackage(
        workspace_id=workspace_id,
        content_department_run_id=run.id,
        creative_direction_id=direction.id,
        strategy_brief_id=brief.id,
        content_item_id=item.id,
        content_version_id=version.id,
        prior_content_version_id=(previous.content_version_id if previous else None),
        revision_reason=(revision_reason if previous else None),
        writer_worker_id=f"writer_{worker_suffix}",
        provider=run.provider_state,
        prompt_version=f"writer-v1-{worker_suffix}",
        input_references={
            "strategy_brief_id": str(brief.id),
            "creative_direction_id": str(direction.id),
            "business_brain_state": run.business_context_state,
        },
        package_fields={
            "primary_hook": script_hook,
            "script": script_body,
            "cta": script_cta,
            "title": script.title,
            "description": script.description,
        },
        status="awaiting_audits",
        audit_gate_status="not_ready",
        producer_handoff_state="blocked",
        test_data=test_data,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(package)
    await session.flush()

    claim_payloads = (
        claim_overrides
        if claim_overrides is not None
        else _extract_claims("\n".join((script_hook, script_body, script_cta)))
    )
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
                test_data=test_data,
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
        test_data=test_data,
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
    await session.flush()
    return direction, package


async def record_fixture_package(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    strategy_brief_id: uuid.UUID,
    fixture: dict[str, Any],
    prior_package_id: uuid.UUID | None = None,
) -> tuple[ContentDepartmentRun, CreativeDirection, ContentPackage]:
    """Test-only entry point onto the shared package persistence path."""
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("fixture content execution is test-only")
    brief = await _require_strategy_pass(
        session, workspace_id=workspace_id, strategy_brief_id=strategy_brief_id
    )
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

    objective = str(fixture.get("objective", brief.objective))
    direction_draft = CreativeDirectionDraft(
        creative_concept=str(fixture.get("creative_concept", objective)),
        opening_pattern=fixture.get("opening_pattern", brief.hook_direction),
        story_structure=fixture.get("story_structure", "problem-evidence-action"),
        tone=fixture.get("tone", "clear"),
        pacing=fixture.get("pacing", "measured"),
        visual_direction=fixture.get("visual_direction", "evidence-led"),
        audio_direction=fixture.get("audio_direction", "clear narration"),
        desired_emotion=fixture.get("desired_emotion", "confidence"),
        production_complexity=fixture.get("production_complexity", "low"),
        estimated_duration=fixture.get("estimated_duration", brief.recommended_length),
        required_claims=list(fixture.get("required_claims", [])),
        prohibited_claims=list(fixture.get("prohibited_claims", [])),
        required_assets=list(fixture.get("required_assets", [])),
        risk_notes=list(fixture.get("risk_notes", [])),
    )
    script = ScriptDraft(
        title=str(fixture.get("title", objective)),
        description=str(fixture.get("description", "TEST DATA")),
        hook=str(fixture.get("hook", "A practical evidence-first opening.")),
        body=str(fixture.get("script", "Use approved evidence and avoid unsupported claims.")),
        cta=str(fixture.get("cta", "Review the evidence before acting.")),
    )
    direction, package = await _persist_content_package(
        session,
        run=run,
        actor_id=actor_id,
        brief=brief,
        objective=objective,
        direction_draft=direction_draft,
        script=script,
        worker_suffix="fixture",
        prior_package_id=prior_package_id,
        target_length_seconds=fixture.get("target_length_seconds"),
        revision_reason=fixture.get("revision_reason"),
        claim_overrides=fixture.get("claims"),
    )
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

    audit = await _persist_content_audit(
        session,
        package=package,
        direction=direction,
        actor_id=actor_id,
        auditor_type=auditor_type,
        auditor_worker_id=f"{auditor_type}_auditor_fixture",
        state=state,
        findings=list(findings or []),
        warnings=list(warnings or []),
        blocked_reasons=list(blocked_reasons or []),
        evidence=list(evidence or []),
    )
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
    provider = get_pipeline_provider()
    if not provider.is_configured:
        return {
            "content_package_id": package.id,
            "eligible": False,
            "state": "provider_not_configured",
            "detail": (
                "Audited Creative Package is structurally eligible for a future Producer; "
                "no Producer provider is configured."
            ),
        }
    return {
        "content_package_id": package.id,
        "eligible": True,
        "state": "eligible",
        "detail": "Audited Creative Package is eligible for Producer handoff.",
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
    provider = get_pipeline_provider()
    return {
        "provider_state": provider.state_label,
        "status": last.status if last else "not_configured",
        "current_run": current,
        "last_run": last,
        "creative_directions": directions,
        "packages_ready": package_counts[1],
        "packages_blocked": package_counts[2],
        "packages_in_progress": package_counts[3],
        "claims_unverified": unverified,
        "cost_today_usd": sum(
            (Decimal(str(run.actual_cost_usd)) for run in runs), Decimal("0.00")
        ),
        "last_error": last.last_error if last else "CONTENT PROVIDER NOT CONFIGURED",
        "schedule_enabled": False,
        "business_context_state": "complete" if provider.is_configured else "incomplete",
        "performance_data_state": "no_data",
    }
