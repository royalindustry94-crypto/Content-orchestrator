"""Prometheus-format operational metrics (aggregate, no tenant secrets)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.orchestration import metrics as metrics_mod

router = APIRouter(tags=["metrics"])


def _prom_line(name: str, value: float | int, labels: dict[str, str] | None = None) -> str:
    if labels:
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}} {value}"
    return f"{name} {value}"


async def _collect(session: AsyncSession) -> str:
    lines: list[str] = [
        "# HELP co_up Content Orchestrator API process up",
        "# TYPE co_up gauge",
        "co_up 1",
    ]

    depth = await metrics_mod.queue_depth(session)
    lines.append("# HELP co_job_schedule_depth Job schedule rows by status")
    lines.append("# TYPE co_job_schedule_depth gauge")
    for status, count in sorted(depth.items()):
        lines.append(_prom_line("co_job_schedule_depth", count, {"status": status}))

    latency = await metrics_mod.event_latency_seconds(session)
    lines.append("# HELP co_outbox_dispatch_latency_seconds Avg outbox dispatch latency")
    lines.append("# TYPE co_outbox_dispatch_latency_seconds gauge")
    lines.append(
        _prom_line(
            "co_outbox_dispatch_latency_seconds",
            latency["avg_dispatch_latency_seconds"],
        )
    )

    duration = await metrics_mod.workflow_execution_duration_seconds(session)
    lines.append("# HELP co_pipeline_execution_duration_seconds Avg completed run duration")
    lines.append("# TYPE co_pipeline_execution_duration_seconds gauge")
    lines.append(
        _prom_line(
            "co_pipeline_execution_duration_seconds",
            duration["avg_execution_duration_seconds"],
        )
    )

    retries = await metrics_mod.retry_counts(session)
    lines.append("# HELP co_stage_failures_24h Failed stage runs in last 24h")
    lines.append("# TYPE co_stage_failures_24h gauge")
    lines.append(_prom_line("co_stage_failures_24h", retries))

    dlq = await metrics_mod.dead_letter_count(session)
    lines.append("# HELP co_dead_letter_pending Pending dead-letter jobs")
    lines.append("# TYPE co_dead_letter_pending gauge")
    lines.append(_prom_line("co_dead_letter_pending", dlq))

    rates = await metrics_mod.dispatch_success_failure_rate(session)
    lines.append("# HELP co_assignment_success_rate Assignment success rate (24h)")
    lines.append("# TYPE co_assignment_success_rate gauge")
    lines.append(_prom_line("co_assignment_success_rate", rates["success_rate"]))
    lines.append("# HELP co_assignment_failure_rate Assignment failure rate (24h)")
    lines.append("# TYPE co_assignment_failure_rate gauge")
    lines.append(_prom_line("co_assignment_failure_rate", rates["failure_rate"]))

    contention = await metrics_mod.worker_lease_contention(session)
    lines.append("# HELP co_lease_contention Expired leases not yet reaped")
    lines.append("# TYPE co_lease_contention gauge")
    lines.append(_prom_line("co_lease_contention", contention))

    throughput = await metrics_mod.scheduler_throughput(session)
    lines.append("# HELP co_scheduler_done_5m Jobs marked done in last 5 minutes")
    lines.append("# TYPE co_scheduler_done_5m gauge")
    lines.append(_prom_line("co_scheduler_done_5m", throughput))

    lines.append("")
    return "\n".join(lines)


@router.get("/metrics")
async def prometheus_metrics() -> Response:
    """Aggregate operational metrics for scrapers. No workspace-scoped data."""
    async with AsyncSessionLocal() as session:
        body = await _collect(session)
    return Response(content=body, media_type="text/plain; version=0.0.4; charset=utf-8")
