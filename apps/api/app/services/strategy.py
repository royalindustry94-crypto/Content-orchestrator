"""Bounded Strategist and independent Strategy Auditor V1 service.

Strategy execution goes through the configured pipeline provider. Without one,
runs persist their limits and return provider-not-configured truthfully. The
independent Strategy Auditor always runs for real against whatever was stored,
regardless of which provider produced it.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import Opportunity
from app.models.strategy import (
    StrategyAudit,
    StrategyBrief,
    StrategyBriefOpportunity,
    StrategyRun,
    StrategySchedule,
)
from app.orchestration.outbox import emit
from app.providers import (
    ProviderExecutionError,
    StrategyBriefDraft,
    StrategyRequest,
    get_pipeline_provider,
)
from app.schemas.strategy import StrategyRunCreate
from app.services import research

_UNTRUSTED_INSTRUCTION = re.compile(
    r"(?i)(ignore\s+(all\s+)?previous|system\s+prompt|developer\s+message|"
    r"reveal\s+(?:secret|token|password)|bypass\s+(?:review|security)|"
    r"execute\s+this\s+instruction)"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|authorization|bearer|oauth|token|password)\s*[:=]\s*[^\s,;]+"
)
_OVERSTATED_PATTERN = re.compile(
    r"(?i)(will\s+go\s+viral|guaranteed\s+(?:winner|success)|expected\s+\d+[km]?\s+views)"
)


class StrategyGateError(ValueError):
    """Raised when a source opportunity has not passed Research Auditor."""


class StrategyAuditGateError(ValueError):
    """Raised when a brief has not passed independent Strategy Auditor."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _safe_text(value: str, *, field: str, maximum: int = 10_000) -> str:
    normalized = value.strip()
    if not normalized or len(normalized) > maximum:
        raise ValueError(f"{field} must be non-empty and at most {maximum} characters")
    if _UNTRUSTED_INSTRUCTION.search(normalized):
        raise ValueError(f"{field} contains an untrusted instruction pattern")
    if _SECRET_PATTERN.search(normalized):
        raise ValueError(f"{field} contains a secret-like value")
    return normalized


def _structural_fingerprint(
    *,
    source_opportunity_ids: list[uuid.UUID],
    objective: str,
    target_platform: str | None,
    content_format: str | None,
    creative_angle: str | None,
    hook_direction: str | None,
    cta_direction: str | None,
    business_goal: str | None,
) -> str:
    material = "\n".join(
        [
            *sorted(str(item) for item in source_opportunity_ids),
            objective.strip().lower(),
            (target_platform or "").strip().lower(),
            (content_format or "").strip().lower(),
            (creative_angle or "").strip().lower(),
            (hook_direction or "").strip().lower(),
            (cta_direction or "").strip().lower(),
            (business_goal or "").strip().lower(),
        ]
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


async def _emit_run(
    session: AsyncSession, run: StrategyRun, event_type: str, payload: dict[str, Any]
) -> None:
    await emit(
        session,
        event_type=event_type,
        workspace_id=run.workspace_id,
        aggregate_type="strategy_run",
        aggregate_id=run.id,
        correlation_id=run.correlation_id,
        trace_id=run.trace_id,
        payload=payload,
        produced_by="strategist-service",
    )


async def get_run(
    session: AsyncSession, *, workspace_id: uuid.UUID, run_id: uuid.UUID
) -> StrategyRun | None:
    return (
        await session.execute(
            select(StrategyRun).where(
                StrategyRun.id == run_id, StrategyRun.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()


async def list_runs(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[StrategyRun]:
    return list(
        (
            await session.execute(
                select(StrategyRun)
                .where(StrategyRun.workspace_id == workspace_id)
                .order_by(StrategyRun.created_at.desc())
            )
        ).scalars()
    )


async def get_brief(
    session: AsyncSession, *, workspace_id: uuid.UUID, brief_id: uuid.UUID
) -> StrategyBrief | None:
    return (
        await session.execute(
            select(StrategyBrief).where(
                StrategyBrief.id == brief_id,
                StrategyBrief.workspace_id == workspace_id,
                StrategyBrief.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def list_briefs(session: AsyncSession, *, workspace_id: uuid.UUID) -> list[StrategyBrief]:
    return list(
        (
            await session.execute(
                select(StrategyBrief)
                .where(
                    StrategyBrief.workspace_id == workspace_id,
                    StrategyBrief.deleted_at.is_(None),
                )
                .order_by(StrategyBrief.created_at.desc())
            )
        ).scalars()
    )


async def brief_opportunity_ids(
    session: AsyncSession, *, workspace_id: uuid.UUID, brief_id: uuid.UUID
) -> list[uuid.UUID]:
    return list(
        (
            await session.execute(
                select(StrategyBriefOpportunity.opportunity_id).where(
                    StrategyBriefOpportunity.workspace_id == workspace_id,
                    StrategyBriefOpportunity.strategy_brief_id == brief_id,
                )
            )
        ).scalars()
    )


async def latest_audit(
    session: AsyncSession, *, workspace_id: uuid.UUID, brief_id: uuid.UUID
) -> StrategyAudit | None:
    return (
        await session.execute(
            select(StrategyAudit)
            .where(
                StrategyAudit.workspace_id == workspace_id,
                StrategyAudit.strategy_brief_id == brief_id,
            )
            .order_by(StrategyAudit.checked_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _require_research_pass(
    session: AsyncSession, *, workspace_id: uuid.UUID, opportunity_ids: list[uuid.UUID]
) -> list[Opportunity]:
    opportunities: list[Opportunity] = []
    for opportunity_id in opportunity_ids:
        try:
            await research.strategist_gate(
                session, workspace_id=workspace_id, opportunity_id=opportunity_id
            )
        except research.ResearchGateError as exc:
            raise StrategyGateError(str(exc)) from exc
        opportunity = await research.get_opportunity(
            session, workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if opportunity is None:
            raise StrategyGateError("source opportunity not found")
        opportunities.append(opportunity)
    return opportunities


async def create_manual_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: StrategyRunCreate,
) -> StrategyRun:
    """Persist a bounded request and execute it through the configured provider.

    Without a configured provider no brief is claimed, no provider is called,
    and nothing is spent.
    """
    provider = get_pipeline_provider()
    objective = _safe_text(payload.strategy_objective, field="strategy objective", maximum=1000)
    opportunity_ids = list(payload.source_opportunity_ids)
    opportunities = await _require_research_pass(
        session, workspace_id=workspace_id, opportunity_ids=opportunity_ids
    )
    now = _utcnow()
    run = StrategyRun(
        workspace_id=workspace_id,
        trigger="manual",
        strategy_objective=objective,
        source_opportunity_ids=[str(item) for item in opportunity_ids],
        started_at=now,
        deadline=now + timedelta(minutes=15),
        max_provider_calls=payload.max_provider_calls,
        max_tokens=payload.max_tokens,
        max_cost_usd=payload.max_cost_usd,
        max_attempts=payload.max_attempts,
        status="running" if provider.is_configured else "provider_not_configured",
        provider_state=provider.state_label,
        business_context_state="complete" if provider.is_configured else "incomplete",
        last_error=(
            None
            if provider.is_configured
            else "STRATEGY PROVIDER NOT CONFIGURED; BUSINESS CONTEXT INCOMPLETE"
        ),
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(run)
    await session.flush()
    await _emit_run(
        session,
        run,
        "strategy.started",
        {
            "trigger": "manual",
            "provider": provider.name,
            "source_opportunity_ids": [str(item) for item in opportunity_ids],
            "limits": {
                "max_provider_calls": run.max_provider_calls,
                "max_tokens": run.max_tokens,
                "max_cost_usd": str(run.max_cost_usd),
                "max_attempts": run.max_attempts,
            },
            "provider_state": run.provider_state,
            "business_context_state": run.business_context_state,
        },
    )
    if not provider.is_configured:
        await _emit_run(
            session,
            run,
            "strategy.provider_not_configured",
            {"detail": run.last_error},
        )
        return run

    try:
        result = await provider.strategy(
            StrategyRequest(
                workspace_id=workspace_id,
                objective=objective,
                opportunity_topics=[item.topic for item in opportunities],
                opportunity_angles=[item.proposed_angle for item in opportunities],
                opportunity_summaries=[item.summary for item in opportunities],
                target_platform=next(
                    (item.target_platform for item in opportunities if item.target_platform),
                    None,
                ),
            )
        )
    except Exception as exc:  # a failed provider call is a failed run, not an unconfigured one
        run.status = "failed"
        run.last_error = f"strategy provider '{provider.name}' failed: {exc}"
        await _emit_run(session, run, "strategy.failed", {"reason": run.last_error})
        return run

    await _persist_strategy_brief(
        session,
        run=run,
        actor_id=actor_id,
        opportunities=opportunities,
        draft=result.brief,
        states={
            "cost_state": "known",
            "capability_state": "configured",
            "business_context_state": "complete",
            "performance_data_state": "no_data",
            "repetition_state": "clear",
            "repetition_reasons": [],
        },
        worker_id=f"strategist_{provider.name}",
    )
    run.provider_calls_used = result.usage.calls
    run.tokens_used = result.usage.tokens
    run.actual_cost_usd = result.usage.cost_usd
    if Decimal(str(run.actual_cost_usd)) > Decimal(str(run.max_cost_usd)):
        raise ProviderExecutionError(
            "strategy provider reported cost above the run's persisted ceiling"
        )
    return run


async def _persist_strategy_brief(
    session: AsyncSession,
    *,
    run: StrategyRun,
    actor_id: uuid.UUID,
    opportunities: list[Opportunity],
    draft: StrategyBriefDraft,
    states: dict[str, Any],
    worker_id: str,
) -> tuple[StrategyBrief, bool]:
    """Store a brief with the same validation and dedupe for every producer.

    Returns the brief and whether it was an existing structural duplicate.
    Provider text is sanitised here rather than at the provider boundary, so a
    future vendor cannot bypass the untrusted-instruction and secret checks.
    """
    workspace_id = run.workspace_id
    test_data = run.test_data
    opportunity_ids = [item.id for item in opportunities]

    def clean(value: str | None, field: str) -> str | None:
        return _safe_text(str(value), field=field) if value is not None else None

    objective = _safe_text(draft.objective, field="brief objective")
    evidence_summary = _safe_text(draft.evidence_summary, field="evidence summary")
    reasoning = _safe_text(draft.reasoning, field="reasoning")
    fingerprint = _structural_fingerprint(
        source_opportunity_ids=opportunity_ids,
        objective=objective,
        target_platform=draft.target_platform,
        content_format=draft.content_format,
        creative_angle=draft.creative_angle,
        hook_direction=draft.hook_direction,
        cta_direction=draft.cta_direction,
        business_goal=draft.business_goal,
    )
    existing = (
        await session.execute(
            select(StrategyBrief).where(
                StrategyBrief.workspace_id == workspace_id,
                StrategyBrief.structural_fingerprint == fingerprint,
                StrategyBrief.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        run.status = "duplicate"
        run.last_error = "DUPLICATE — REUSE OR REVISE"
        await _emit_run(
            session,
            run,
            "strategy.duplicate_detected",
            {"strategy_brief_id": str(existing.id), "test_data": test_data},
        )
        return existing, True

    brief = StrategyBrief(
        workspace_id=workspace_id,
        strategy_run_id=run.id,
        objective=objective,
        target_audience=clean(draft.target_audience, "target_audience"),
        target_platform=clean(draft.target_platform, "target_platform"),
        content_format=clean(draft.content_format, "content_format"),
        creative_angle=clean(draft.creative_angle, "creative_angle"),
        core_message=clean(draft.core_message, "core_message"),
        hook_direction=clean(draft.hook_direction, "hook_direction"),
        cta_direction=clean(draft.cta_direction, "cta_direction"),
        business_goal=clean(draft.business_goal, "business_goal"),
        success_metric=clean(draft.success_metric, "success_metric"),
        commercial_goal=clean(draft.commercial_goal, "commercial_goal"),
        estimated_complexity=draft.estimated_complexity,
        risk_level=draft.risk_level,
        evidence_summary=evidence_summary,
        reasoning=reasoning,
        confidence=draft.confidence,
        priority=draft.priority,
        component_scores=dict(draft.component_scores),
        score_reasoning=dict(draft.score_reasoning),
        recommended_length=clean(draft.recommended_length, "recommended_length"),
        recommended_posting_window=clean(
            draft.recommended_posting_window, "recommended_posting_window"
        ),
        required_assets=list(draft.required_assets),
        production_requirements=list(draft.production_requirements),
        rights_requirements=list(draft.rights_requirements),
        compliance_requirements=list(draft.compliance_requirements),
        estimated_provider_usage=dict(draft.estimated_provider_usage),
        estimated_cost_range=dict(draft.estimated_cost_range),
        cost_state=str(states.get("cost_state", "known")),
        capability_state=str(states.get("capability_state", "configured")),
        business_context_state=str(states.get("business_context_state", "complete")),
        performance_data_state=str(states.get("performance_data_state", "no_data")),
        structural_fingerprint=fingerprint,
        repetition_state=str(states.get("repetition_state", "clear")),
        repetition_reasons=list(states.get("repetition_reasons", [])),
        created_by_worker=worker_id,
        status="draft",
        test_data=test_data,
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(brief)
    await session.flush()
    for opportunity in opportunities:
        session.add(
            StrategyBriefOpportunity(
                workspace_id=workspace_id,
                strategy_brief_id=brief.id,
                opportunity_id=opportunity.id,
            )
        )
    run.briefs_created = 1
    run.status = "succeeded"
    await _emit_run(
        session,
        run,
        "strategy.brief_created",
        {"strategy_brief_id": str(brief.id), "test_data": test_data},
    )
    return brief, False


async def record_fixture_brief(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    objective: str,
    source_opportunity_ids: list[uuid.UUID],
    fixture_brief: dict[str, Any],
) -> tuple[StrategyRun, StrategyBrief, bool]:
    """Test-only entry point onto the shared brief persistence path."""
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("fixture strategy execution is test-only")
    clean_objective = _safe_text(objective, field="strategy objective", maximum=1000)
    opportunities = await _require_research_pass(
        session, workspace_id=workspace_id, opportunity_ids=source_opportunity_ids
    )
    now = _utcnow()
    run = StrategyRun(
        workspace_id=workspace_id,
        trigger="manual_test_fixture",
        strategy_objective=clean_objective,
        source_opportunity_ids=[str(item) for item in source_opportunity_ids],
        started_at=now,
        deadline=now + timedelta(minutes=5),
        max_provider_calls=0,
        max_tokens=0,
        max_cost_usd=Decimal("0.00"),
        max_attempts=1,
        status="running",
        provider_state="fixture_test_only",
        business_context_state=str(fixture_brief.get("business_context_state", "complete")),
        created_by=actor_id,
        updated_by=actor_id,
        test_data=True,
    )
    session.add(run)
    await session.flush()
    await _emit_run(session, run, "strategy.started", {"trigger": run.trigger, "test_data": True})

    def optional(name: str) -> str | None:
        value = fixture_brief.get(name)
        return str(value) if value is not None else None

    draft = StrategyBriefDraft(
        objective=str(fixture_brief.get("objective", clean_objective)),
        target_audience=optional("target_audience"),
        target_platform=optional("target_platform"),
        content_format=optional("content_format"),
        creative_angle=optional("creative_angle"),
        core_message=optional("core_message"),
        hook_direction=optional("hook_direction"),
        cta_direction=optional("cta_direction"),
        business_goal=optional("business_goal"),
        success_metric=optional("success_metric"),
        commercial_goal=optional("commercial_goal"),
        evidence_summary=str(fixture_brief.get("evidence_summary", opportunities[0].summary)),
        reasoning=str(fixture_brief.get("reasoning", opportunities[0].proposed_angle)),
        confidence=Decimal(str(fixture_brief.get("confidence", "0.50"))),
        priority=str(fixture_brief.get("priority", "medium_priority")),
        estimated_complexity=str(fixture_brief.get("estimated_complexity", "low")),
        risk_level=str(fixture_brief.get("risk_level", "low")),
        recommended_length=optional("recommended_length"),
        recommended_posting_window=optional("recommended_posting_window"),
        required_assets=list(fixture_brief.get("required_assets", [])),
        production_requirements=list(fixture_brief.get("production_requirements", [])),
        rights_requirements=list(fixture_brief.get("rights_requirements", [])),
        compliance_requirements=list(fixture_brief.get("compliance_requirements", [])),
        component_scores=dict(fixture_brief.get("component_scores", {})),
        score_reasoning=dict(fixture_brief.get("score_reasoning", {})),
        estimated_provider_usage=dict(fixture_brief.get("estimated_provider_usage", {})),
        estimated_cost_range=dict(fixture_brief.get("estimated_cost_range", {})),
    )
    brief, duplicate = await _persist_strategy_brief(
        session,
        run=run,
        actor_id=actor_id,
        opportunities=opportunities,
        draft=draft,
        states={
            "cost_state": fixture_brief.get("cost_state", "known"),
            "capability_state": fixture_brief.get("capability_state", "configured"),
            "business_context_state": fixture_brief.get("business_context_state", "complete"),
            "performance_data_state": fixture_brief.get("performance_data_state", "no_data"),
            "repetition_state": fixture_brief.get("repetition_state", "clear"),
            "repetition_reasons": fixture_brief.get("repetition_reasons", []),
        },
        worker_id="strategist_fixture",
    )
    return run, brief, duplicate


async def audit_brief(
    session: AsyncSession, *, workspace_id: uuid.UUID, brief_id: uuid.UUID
) -> StrategyAudit:
    """Independently inspect persisted brief inputs; never trust Strategist output."""
    brief = await get_brief(session, workspace_id=workspace_id, brief_id=brief_id)
    if brief is None:
        raise LookupError("strategy brief not found")
    source_ids = await brief_opportunity_ids(session, workspace_id=workspace_id, brief_id=brief_id)
    findings: list[dict[str, str]] = []
    warnings: list[str] = []
    blocked: list[str] = []
    if not source_ids:
        blocked.append("No source opportunities are linked to this Strategy Brief.")
    for opportunity_id in source_ids:
        audit = await research.latest_audit(
            session, workspace_id=workspace_id, opportunity_id=opportunity_id
        )
        if audit is None or audit.state != "pass":
            blocked.append("Research Auditor PASS is required for every source opportunity.")
            break
        findings.append(
            {
                "opportunity_id": str(opportunity_id),
                "research_audit_state": audit.state,
                "evidence_traceability": "pass",
            }
        )
    if brief.business_context_state != "complete" or not brief.business_goal:
        blocked.append("BUSINESS CONTEXT INCOMPLETE")
    if not brief.target_platform or not brief.content_format:
        blocked.append("Target platform and content format are required.")
    if brief.cost_state in {"unknown", "not_configured"}:
        blocked.append("COST UNKNOWN")
    if brief.capability_state != "configured":
        blocked.append("BLOCKED — REQUIRED CAPABILITY NOT CONFIGURED")
    if brief.repetition_state in {"duplicate", "require_differentiation", "blocked"}:
        blocked.extend(brief.repetition_reasons or ["Materially repetitive strategy."])
    if _OVERSTATED_PATTERN.search(brief.reasoning) or _OVERSTATED_PATTERN.search(
        brief.evidence_summary
    ):
        blocked.append("Unsupported performance or commercial guarantee detected.")
    if brief.performance_data_state != "no_data":
        warnings.append("Performance-data state requires a source-backed future check.")
    state = "blocked" if blocked else ("pass_with_warning" if warnings else "pass")
    snapshot = {
        "objective": brief.objective,
        "business_goal": brief.business_goal,
        "target_platform": brief.target_platform,
        "content_format": brief.content_format,
        "structural_fingerprint": brief.structural_fingerprint,
        "cost_state": brief.cost_state,
        "capability_state": brief.capability_state,
        "business_context_state": brief.business_context_state,
        "repetition_state": brief.repetition_state,
    }
    audit = StrategyAudit(
        workspace_id=workspace_id,
        strategy_brief_id=brief.id,
        strategy_run_id=brief.strategy_run_id,
        state=state,
        brief_snapshot=snapshot,
        findings=findings,
        warnings=warnings,
        blocked_reasons=blocked,
        test_data=brief.test_data,
    )
    session.add(audit)
    brief.audit_gate_status = state
    brief.writer_handoff_state = "eligible" if state == "pass" else "blocked"
    brief.status = "audited_passed" if state == "pass" else "audited_blocked"
    run = await get_run(session, workspace_id=workspace_id, run_id=brief.strategy_run_id)
    if run is not None:
        if state == "pass":
            run.briefs_passed += 1
        else:
            run.briefs_blocked += 1
    await session.flush()
    if run is not None:
        await _emit_run(
            session,
            run,
            f"strategy.audit.{state}",
            {
                "strategy_brief_id": str(brief.id),
                "audit_id": str(audit.id),
                "test_data": brief.test_data,
            },
        )
    return audit


async def writer_gate(
    session: AsyncSession, *, workspace_id: uuid.UUID, brief_id: uuid.UUID
) -> dict[str, Any]:
    brief = await get_brief(session, workspace_id=workspace_id, brief_id=brief_id)
    if brief is None:
        raise LookupError("strategy brief not found")
    audit = await latest_audit(session, workspace_id=workspace_id, brief_id=brief_id)
    if audit is None or audit.state != "pass":
        detail = "Independent Strategy Auditor PASS is required before Writer eligibility."
        run = await get_run(session, workspace_id=workspace_id, run_id=brief.strategy_run_id)
        if run is not None:
            await _emit_run(
                session,
                run,
                "strategy.writer_denied",
                {
                    "strategy_brief_id": str(brief.id),
                    "audit_state": audit.state if audit else "not_run",
                },
            )
        raise StrategyAuditGateError(detail)
    brief.writer_handoff_state = "eligible"
    run = await get_run(session, workspace_id=workspace_id, run_id=brief.strategy_run_id)
    if run is not None:
        await _emit_run(
            session,
            run,
            "strategy.writer_eligible",
            {"strategy_brief_id": str(brief.id), "test_data": brief.test_data},
        )
    provider = get_pipeline_provider()
    return {
        "strategy_brief_id": brief.id,
        "eligible": True,
        "state": "eligible",
        "detail": (
            "Strategy is eligible for a Writer handoff."
            if provider.is_configured
            else (
                "Strategy is eligible for a future Writer handoff; "
                "no Writer provider is configured."
            )
        ),
    }


async def summary(session: AsyncSession, *, workspace_id: uuid.UUID) -> dict[str, Any]:
    runs = await list_runs(session, workspace_id=workspace_id)
    current = next((run for run in runs if run.status == "running"), None)
    last = runs[0] if runs else None
    counts = (
        await session.execute(
            select(
                func.count(StrategyBrief.id),
                func.count(StrategyBrief.id).filter(StrategyBrief.audit_gate_status == "pass"),
                func.count(StrategyBrief.id).filter(StrategyBrief.audit_gate_status != "pass"),
            ).where(
                StrategyBrief.workspace_id == workspace_id,
                StrategyBrief.deleted_at.is_(None),
            )
        )
    ).one()
    schedule = (
        await session.execute(
            select(StrategySchedule).where(StrategySchedule.workspace_id == workspace_id)
        )
    ).scalar_one_or_none()
    received = (
        await session.execute(
            select(func.count(Opportunity.id)).where(
                Opportunity.workspace_id == workspace_id,
                Opportunity.audit_gate_status == "pass",
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one()
    cost = sum((Decimal(str(run.actual_cost_usd)) for run in runs), Decimal("0"))
    provider = get_pipeline_provider()
    return {
        "provider_state": provider.state_label,
        "status": current.status if current else (last.status if last else "not_run"),
        "current_strategy": current,
        "last_run": last,
        "next_run_at": schedule.next_run_at if schedule and schedule.enabled else None,
        "opportunities_received": int(received or 0),
        "briefs_created": int(counts[0] or 0),
        "briefs_passed": int(counts[1] or 0),
        "briefs_blocked": int(counts[2] or 0),
        "cost_today_usd": cost,
        "last_error": (current or last).last_error
        if (current or last)
        else "STRATEGY PROVIDER NOT CONFIGURED",
        "schedule_enabled": bool(schedule.enabled) if schedule else False,
        "business_context_state": "complete" if provider.is_configured else "incomplete",
        "performance_data_state": "no_data",
    }
