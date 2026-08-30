"""Bounded Scout research and independent Research Auditor service.

Research execution goes through the configured pipeline provider. With the
default ``null`` provider there is no external research vendor, so manual runs
persist their limits and truthfully finish as ``provider_not_configured``. With
a configured provider the same persistence, provenance, deduplication, and
independent audit gates run against that provider's output, labelled with the
provider's own state so stored evidence is never misattributed.

The test fixture path shares that persistence routine so regression tests
exercise the code that really runs.
"""

from __future__ import annotations

import hashlib
import ipaddress
import os
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.research import (
    Opportunity,
    OpportunityEvidence,
    ResearchAudit,
    ResearchRun,
    ResearchSchedule,
    ResearchSource,
)
from app.orchestration.outbox import emit
from app.providers import (
    OpportunityDraft,
    ProviderExecutionError,
    ResearchRequest,
    SourceDraft,
    get_pipeline_provider,
)
from app.schemas.research import ResearchRunCreate

MAX_FIXTURE_EXCERPT = 6_000
_UNTRUSTED_INSTRUCTION = re.compile(
    r"(?i)(ignore\s+(all\s+)?previous|system\s+prompt|developer\s+message|"
    r"reveal\s+(?:secret|token|password)|bypass\s+(?:review|security)|"
    r"execute\s+this\s+instruction)"
)
_SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|authorization|bearer|oauth|token|password)\s*[:=]\s*[^\s,;]+"
)


class ResearchGateError(ValueError):
    """Raised when an opportunity has not passed independent research audit."""


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _canonical_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
    ):
        raise ValueError(
            "source URL must be a public http(s) URL without embedded credentials"
        )
    host = parsed.hostname.lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"}:
        raise ValueError("private or localhost source URL is not permitted")
    try:
        address = ipaddress.ip_address(host)
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
        ):
            raise ValueError("private or local source URL is not permitted")
    except ValueError as exc:
        if "private or local" in str(exc):
            raise
    path = parsed.path.rstrip("/") or "/"
    return urlunsplit((parsed.scheme.lower(), host, path, parsed.query, ""))


def _safe_excerpt(value: str | None) -> tuple[str | None, str | None]:
    if value is None:
        return None, None
    bounded = value.strip()[:MAX_FIXTURE_EXCERPT]
    if _UNTRUSTED_INSTRUCTION.search(bounded):
        return None, "untrusted instruction pattern detected"
    return _SECRET_PATTERN.sub("[REDACTED_SECRET]", bounded), None


def _dedupe_key(
    *,
    topic: str,
    angle: str,
    platform: str | None,
    format_name: str | None,
    source_urls: list[str],
) -> str:
    material = "\n".join(
        [
            topic.strip().lower(),
            angle.strip().lower(),
            (platform or "").strip().lower(),
            (format_name or "").strip().lower(),
        ]
        + sorted(source_urls)
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _run_is_terminal(status: str) -> bool:
    return status in {
        "succeeded",
        "provider_not_configured",
        "budget_exhausted",
        "timeout",
        "source_limit_reached",
        "failed",
        "cancelled",
    }


async def _emit_run(
    session: AsyncSession, run: ResearchRun, event_type: str, payload: dict
) -> None:
    await emit(
        session,
        event_type=event_type,
        workspace_id=run.workspace_id,
        aggregate_type="research_run",
        aggregate_id=run.id,
        correlation_id=run.correlation_id,
        trace_id=run.trace_id,
        payload=payload,
        produced_by="scout-service",
    )


async def create_manual_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    payload: ResearchRunCreate,
) -> ResearchRun:
    """Persist a bounded manual run and execute it through the configured provider.

    Without a configured provider the run stops at ``provider_not_configured``
    and makes no external call and no spend.
    """
    provider = get_pipeline_provider()
    now = _utcnow()
    # Runs are deliberately short-lived; a provider must honor the persisted
    # deadline rather than invent a longer horizon.
    deadline = now + timedelta(minutes=15)
    objective = payload.research_objective.strip()
    run = ResearchRun(
        workspace_id=workspace_id,
        trigger="manual",
        research_objective=objective,
        permitted_sources=list(payload.permitted_sources),
        started_at=now,
        deadline=deadline,
        max_searches=payload.max_searches,
        max_provider_calls=payload.max_provider_calls,
        max_tokens=payload.max_tokens,
        max_cost_usd=payload.max_cost_usd,
        max_attempts=payload.max_attempts,
        status="queued" if provider.is_configured else "provider_not_configured",
        provider_state=provider.state_label,
        last_error=None if provider.is_configured else "RESEARCH PROVIDER NOT CONFIGURED",
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(run)
    await session.flush()
    await _emit_run(
        session,
        run,
        "research.started",
        {
            "trigger": "manual",
            "provider": provider.name,
            "limits": {
                "max_searches": run.max_searches,
                "max_provider_calls": run.max_provider_calls,
                "max_tokens": run.max_tokens,
                "max_cost_usd": str(run.max_cost_usd),
                "max_attempts": run.max_attempts,
            },
        },
    )
    if not provider.is_configured:
        await _emit_run(
            session,
            run,
            "research.provider_not_configured",
            {"detail": "No external research provider is configured."},
        )
        return run

    try:
        result = await provider.research(
            ResearchRequest(
                workspace_id=workspace_id,
                objective=objective,
                permitted_sources=list(payload.permitted_sources),
                max_searches=payload.max_searches,
            )
        )
    except Exception as exc:  # provider failure is a failed run, never an unconfigured one
        run.status = "failed"
        run.last_error = f"research provider '{provider.name}' failed: {exc}"
        await _emit_run(session, run, "research.failed", {"reason": run.last_error})
        return run

    run.status = "running"
    await _persist_research_output(
        session,
        run=run,
        actor_id=actor_id,
        sources=result.sources,
        opportunity=result.opportunity,
    )
    run.provider_calls_used = result.usage.calls
    run.tokens_used = result.usage.tokens
    run.actual_cost_usd = result.usage.cost_usd
    if Decimal(str(run.actual_cost_usd)) > Decimal(str(run.max_cost_usd)):
        raise ProviderExecutionError(
            "research provider reported cost above the run's persisted ceiling"
        )
    return run


async def list_runs(
    session: AsyncSession, *, workspace_id: uuid.UUID, limit: int = 50
) -> list[ResearchRun]:
    result = await session.execute(
        select(ResearchRun)
        .where(ResearchRun.workspace_id == workspace_id)
        .order_by(ResearchRun.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_run(
    session: AsyncSession, *, workspace_id: uuid.UUID, run_id: uuid.UUID
) -> ResearchRun | None:
    return (
        await session.execute(
            select(ResearchRun).where(
                ResearchRun.workspace_id == workspace_id, ResearchRun.id == run_id
            )
        )
    ).scalar_one_or_none()


async def list_opportunities(
    session: AsyncSession, *, workspace_id: uuid.UUID, limit: int = 100
) -> list[Opportunity]:
    result = await session.execute(
        select(Opportunity)
        .where(
            Opportunity.workspace_id == workspace_id, Opportunity.deleted_at.is_(None)
        )
        .order_by(Opportunity.discovered_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def get_opportunity(
    session: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> Opportunity | None:
    return (
        await session.execute(
            select(Opportunity).where(
                Opportunity.workspace_id == workspace_id,
                Opportunity.id == opportunity_id,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()


async def opportunity_evidence(
    session: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> list[tuple[OpportunityEvidence, ResearchSource]]:
    result = await session.execute(
        select(OpportunityEvidence, ResearchSource)
        .join(ResearchSource, ResearchSource.id == OpportunityEvidence.source_id)
        .where(
            OpportunityEvidence.workspace_id == workspace_id,
            OpportunityEvidence.opportunity_id == opportunity_id,
            ResearchSource.workspace_id == workspace_id,
        )
        .order_by(ResearchSource.retrieved_at.desc())
    )
    return list(result.all())


async def latest_audit(
    session: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> ResearchAudit | None:
    return (
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


async def summary(session: AsyncSession, *, workspace_id: uuid.UUID) -> dict[str, Any]:
    runs = await list_runs(session, workspace_id=workspace_id, limit=2)
    current = next((run for run in runs if not _run_is_terminal(run.status)), None)
    last = runs[0] if runs else None
    counts = (
        await session.execute(
            select(
                func.count(Opportunity.id),
                func.count(Opportunity.id).filter(
                    Opportunity.audit_gate_status != "not_run"
                ),
                func.count(Opportunity.id).filter(
                    Opportunity.audit_gate_status == "blocked"
                ),
            ).where(
                Opportunity.workspace_id == workspace_id,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).one()
    schedule = (
        await session.execute(
            select(ResearchSchedule).where(
                ResearchSchedule.workspace_id == workspace_id
            )
        )
    ).scalar_one_or_none()
    cost = sum((Decimal(str(run.actual_cost_usd)) for run in runs), Decimal("0"))
    provider = get_pipeline_provider()
    return {
        "provider_state": provider.state_label,
        "status": current.status if current else (last.status if last else "not_run"),
        "current_research": current,
        "last_run": last,
        "next_run_at": schedule.next_run_at if schedule and schedule.enabled else None,
        "opportunities_found": int(counts[0] or 0),
        "audited_opportunities": int(counts[1] or 0),
        "blocked_findings": int(counts[2] or 0),
        "cost_today_usd": cost,
        "last_error": (current or last).last_error
        if (current or last)
        else "RESEARCH PROVIDER NOT CONFIGURED",
        "schedule_enabled": bool(schedule.enabled) if schedule else False,
        "research_data_state": "connected" if provider.is_configured else "not_connected",
    }


async def _persist_research_output(
    session: AsyncSession,
    *,
    run: ResearchRun,
    actor_id: uuid.UUID,
    sources: list[SourceDraft],
    opportunity: OpportunityDraft,
) -> Opportunity | None:
    """Store provider output with full provenance, dedupe, and safety handling.

    Shared by the live provider path and the test fixture path so both exercise
    the same URL canonicalisation, excerpt sanitising, and deduplication.
    """
    workspace_id = run.workspace_id
    now = run.started_at
    test_data = run.test_data
    accepted: list[ResearchSource] = []
    for item in sources[: run.max_searches]:
        try:
            url = _canonical_url(item.canonical_url)
        except ValueError as exc:
            await _emit_run(
                session,
                run,
                "research.source_rejected",
                {"reason": str(exc), "test_data": test_data},
            )
            continue
        excerpt, rejection_reason = _safe_excerpt(item.excerpt)
        source = ResearchSource(
            workspace_id=workspace_id,
            research_run_id=run.id,
            canonical_url=url,
            source_type=item.source_type,
            retrieved_at=now,
            published_at=item.published_at,
            publisher=item.publisher,
            author=item.author,
            claim_supported=item.claim_supported,
            freshness=item.freshness,
            confidence=item.confidence,
            content_digest=hashlib.sha256(
                (excerpt or rejection_reason or url).encode("utf-8")
            ).hexdigest(),
            safe_excerpt=excerpt,
            handling_state="rejected" if rejection_reason else "accepted",
            rejection_reason=rejection_reason,
            test_data=test_data,
        )
        session.add(source)
        await session.flush()
        if rejection_reason:
            await _emit_run(
                session,
                run,
                "research.source_rejected",
                {
                    "source_id": str(source.id),
                    "reason": rejection_reason,
                    "test_data": test_data,
                },
            )
        else:
            accepted.append(source)
            await _emit_run(
                session,
                run,
                "research.source_recorded",
                {"source_id": str(source.id), "test_data": test_data},
            )

    run.searches_used = len(sources)
    if not accepted:
        run.status = "failed"
        run.last_error = "No safe evidence sources were accepted"
        await _emit_run(
            session,
            run,
            "research.failed",
            {"reason": run.last_error, "test_data": test_data},
        )
        return None

    topic = opportunity.topic.strip()
    angle = opportunity.proposed_angle.strip()
    key = _dedupe_key(
        topic=topic,
        angle=angle,
        platform=opportunity.target_platform,
        format_name=opportunity.suggested_format,
        source_urls=[s.canonical_url for s in accepted],
    )
    existing = (
        await session.execute(
            select(Opportunity).where(
                Opportunity.workspace_id == workspace_id,
                Opportunity.dedupe_key == key,
                Opportunity.deleted_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing is None:
        record = Opportunity(
            workspace_id=workspace_id,
            research_run_id=run.id,
            title=opportunity.title.strip(),
            topic=topic,
            summary=opportunity.summary.strip(),
            proposed_angle=angle,
            target_audience=opportunity.target_audience,
            target_platform=opportunity.target_platform,
            suggested_format=opportunity.suggested_format,
            freshness=opportunity.freshness,
            source_count=len(accepted),
            confidence=opportunity.confidence,
            risk=opportunity.risk,
            status="active",
            created_by_worker=f"scout_{run.provider_state}",
            component_scores=dict(opportunity.component_scores),
            score_reasoning=dict(opportunity.score_reasoning),
            dedupe_key=key,
            test_data=test_data,
            created_by=actor_id,
            updated_by=actor_id,
        )
        session.add(record)
        await session.flush()
        event_type = "opportunity.created"
    else:
        record = existing
        record.source_count += len(accepted)
        record.updated_by = actor_id
        event_type = "opportunity.duplicate_detected"

    for source in accepted:
        link = OpportunityEvidence(
            workspace_id=workspace_id,
            opportunity_id=record.id,
            source_id=source.id,
            claim_supported=source.claim_supported or record.summary,
            relevance=Decimal("0.80"),
            contradiction_flag=False,
        )
        session.add(link)
    await session.flush()
    await _emit_run(
        session,
        run,
        event_type,
        {"opportunity_id": str(record.id), "test_data": test_data},
    )
    run.opportunity_count = 1 if existing is None else 0
    run.status = "succeeded"
    await _emit_run(
        session,
        run,
        "research.completed",
        {"opportunity_id": str(record.id), "test_data": test_data},
    )
    return record


async def record_fixture_run(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    objective: str,
    fixture_sources: list[dict[str, Any]],
    fixture_opportunity: dict[str, Any],
) -> tuple[ResearchRun, Opportunity | None]:
    """Test-only entry point onto the shared persistence path."""
    if os.getenv("ENVIRONMENT") != "test":
        raise RuntimeError("fixture research execution is test-only")
    now = _utcnow()
    run = ResearchRun(
        workspace_id=workspace_id,
        trigger="manual_test_fixture",
        research_objective=objective,
        permitted_sources=[str(source.get("url", "")) for source in fixture_sources],
        started_at=now,
        deadline=now + timedelta(minutes=5),
        max_searches=max(1, len(fixture_sources)),
        max_provider_calls=0,
        max_tokens=0,
        max_cost_usd=Decimal("0.00"),
        max_attempts=1,
        status="running",
        provider_state="fixture_test_only",
        created_by=actor_id,
        updated_by=actor_id,
        test_data=True,
    )
    session.add(run)
    await session.flush()
    await _emit_run(
        session,
        run,
        "research.started",
        {"trigger": "manual_test_fixture", "test_data": True},
    )
    opportunity = await _persist_research_output(
        session,
        run=run,
        actor_id=actor_id,
        sources=[
            SourceDraft(
                canonical_url=str(item.get("url", "")),
                source_type=str(item.get("source_type", "fixture")),
                publisher=item.get("publisher"),
                author=item.get("author"),
                claim_supported=item.get("claim_supported"),
                freshness=str(item.get("freshness", "test")),
                confidence=Decimal(str(item.get("confidence", "0.50"))),
                excerpt=item.get("excerpt"),
                published_at=item.get("published_at"),
            )
            for item in fixture_sources
        ],
        opportunity=OpportunityDraft(
            title=str(fixture_opportunity["title"]),
            topic=str(fixture_opportunity["topic"]),
            summary=str(fixture_opportunity["summary"]),
            proposed_angle=str(fixture_opportunity["proposed_angle"]),
            target_audience=fixture_opportunity.get("target_audience"),
            target_platform=fixture_opportunity.get("target_platform"),
            suggested_format=fixture_opportunity.get("suggested_format"),
            freshness=str(fixture_opportunity.get("freshness", "test")),
            confidence=Decimal(str(fixture_opportunity.get("confidence", "0.50"))),
            risk=str(fixture_opportunity.get("risk", "low")),
            component_scores=dict(fixture_opportunity.get("component_scores", {})),
            score_reasoning=dict(fixture_opportunity.get("score_reasoning", {})),
        ),
    )
    return run, opportunity


async def audit_opportunity(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    opportunity_id: uuid.UUID,
) -> ResearchAudit:
    """Independently evaluate stored source properties, never Scout’s conclusion."""
    opportunity = await get_opportunity(
        session, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if opportunity is None:
        raise LookupError("opportunity not found")
    evidence = await opportunity_evidence(
        session, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    sources = [source for _, source in evidence]
    findings: list[dict[str, str]] = []
    warnings: list[str] = []
    blocked: list[str] = []
    accepted = [source for source in sources if source.handling_state == "accepted"]
    rejected = [source for source in sources if source.handling_state == "rejected"]
    if not accepted:
        blocked.append("No accepted source provenance supports this opportunity.")
    if rejected:
        blocked.append("At least one source was rejected as unsafe or unverified.")
    if len({source.content_digest for source in accepted}) < len(accepted):
        blocked.append("Duplicate source content detected.")
    if len(accepted) == 1 and not blocked:
        warnings.append("Only one independent accepted source is available.")
    if (
        any(source.freshness in {"stale", "unknown"} for source in accepted)
        and not blocked
    ):
        warnings.append("At least one accepted source has stale or unknown freshness.")
    for source in accepted:
        findings.append(
            {
                "source_id": str(source.id),
                "legitimacy": "accepted_provenance",
                "freshness": source.freshness,
                "claim_support": "present" if source.claim_supported else "missing",
            }
        )
    state = "blocked" if blocked else ("pass_with_warning" if warnings else "pass")
    snapshot = {
        "title": opportunity.title,
        "topic": opportunity.topic,
        "summary": opportunity.summary,
        "proposed_angle": opportunity.proposed_angle,
        "source_count": opportunity.source_count,
        "component_scores": opportunity.component_scores,
    }
    audit = ResearchAudit(
        workspace_id=workspace_id,
        opportunity_id=opportunity.id,
        research_run_id=opportunity.research_run_id,
        state=state,
        scout_snapshot=snapshot,
        findings=findings,
        warnings=warnings,
        blocked_reasons=blocked,
        test_data=opportunity.test_data,
    )
    session.add(audit)
    opportunity.audit_gate_status = state
    if state == "blocked":
        opportunity.status = "blocked"
    run = await get_run(
        session, workspace_id=workspace_id, run_id=opportunity.research_run_id
    )
    if run is not None:
        run.audited_opportunity_count += 1
        if state == "blocked":
            run.blocked_opportunity_count += 1
    await session.flush()
    if run is not None:
        await _emit_run(
            session,
            run,
            f"research.audit.{state}",
            {
                "opportunity_id": str(opportunity.id),
                "audit_id": str(audit.id),
                "test_data": opportunity.test_data,
            },
        )
    return audit


async def strategist_gate(
    session: AsyncSession, *, workspace_id: uuid.UUID, opportunity_id: uuid.UUID
) -> dict[str, Any]:
    opportunity = await get_opportunity(
        session, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if opportunity is None:
        raise LookupError("opportunity not found")
    audit = await latest_audit(
        session, workspace_id=workspace_id, opportunity_id=opportunity_id
    )
    if audit is None or audit.state != "pass":
        detail = "Independent Research Auditor PASS is required before Strategist eligibility."
        run = await get_run(
            session, workspace_id=workspace_id, run_id=opportunity.research_run_id
        )
        if run is not None:
            await _emit_run(
                session,
                run,
                "opportunity.strategist_denied",
                {
                    "opportunity_id": str(opportunity.id),
                    "audit_state": audit.state if audit else "not_run",
                },
            )
        raise ResearchGateError(detail)
    opportunity.strategist_state = "eligible"
    run = await get_run(
        session, workspace_id=workspace_id, run_id=opportunity.research_run_id
    )
    if run is not None:
        await _emit_run(
            session,
            run,
            "opportunity.strategist_eligible",
            {"opportunity_id": str(opportunity.id)},
        )
    provider = get_pipeline_provider()
    return {
        "opportunity_id": opportunity.id,
        "eligible": True,
        "state": "eligible",
        "detail": (
            "Approved intelligence is eligible for a Strategist handoff."
            if provider.is_configured
            else (
                "Approved intelligence is eligible for a future Strategist handoff; "
                "no Strategist provider is configured."
            )
        ),
    }
