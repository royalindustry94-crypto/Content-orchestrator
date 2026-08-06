"""Read-only Operations Dashboard API contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class DeploymentInfo(BaseModel):
    ci_status: str
    ci_url: str | None
    git_branch: str | None
    commit_sha: str | None
    deployed_at: datetime | None


class ExecutiveDashboardOut(BaseModel):
    workers_online: int
    workers_busy: int
    jobs_running: int
    jobs_queued: int
    jobs_failed: int
    human_reviews_waiting: int
    spend_today_usd: Decimal
    spend_month_usd: Decimal
    active_workspaces: int
    deployment: DeploymentInfo
    generated_at: datetime


class WorkerMonitorRow(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    current_job: str | None
    queue: int
    last_heartbeat_at: datetime | None
    retry_count: int
    jobs_completed: int
    jobs_failed: int
    lease_status: str


class WorkerMonitorOut(BaseModel):
    workers: list[WorkerMonitorRow]
    generated_at: datetime


class PipelineRow(BaseModel):
    id: uuid.UUID
    status: str
    current_stage: str
    pause_reason: str | None
    created_at: datetime
    updated_at: datetime


class PipelineMonitorOut(BaseModel):
    active_pipelines: int
    queue_depth: int
    failed_pipelines: int
    retrying_pipelines: int
    dead_letter_queue: int
    review_gates: int
    publish_queue: int
    pipelines: list[PipelineRow]
    generated_at: datetime


class OperationsAlert(BaseModel):
    key: str
    severity: str
    title: str
    count: int
    message: str


class AlertsOut(BaseModel):
    alerts: list[OperationsAlert]
    generated_at: datetime
