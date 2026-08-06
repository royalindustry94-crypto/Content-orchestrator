"""Operations Dashboard V3 — Mission Control API contracts."""

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ActivityItem(BaseModel):
    id: str
    kind: str
    title: str
    detail: str | None
    severity: str
    occurred_at: datetime
    source: str


class ActivityFeedOut(BaseModel):
    items: list[ActivityItem]
    generated_at: datetime


class HealthIndicator(BaseModel):
    key: str
    label: str
    status: str  # green | amber | red
    detail: str


class SystemHealthOut(BaseModel):
    indicators: list[HealthIndicator]
    generated_at: datetime


class CostProviderRow(BaseModel):
    provider: str
    today_usd: Decimal
    month_usd: Decimal


class ExpensiveJobRow(BaseModel):
    pipeline_run_id: uuid.UUID | None
    content_item_id: uuid.UUID | None
    topic: str | None
    stage: str | None
    provider: str | None
    cost_usd: Decimal
    completed_at: datetime | None


class CostControlOut(BaseModel):
    daily_ai_spend_usd: Decimal
    monthly_ai_spend_usd: Decimal
    budget_remaining_daily_usd: Decimal | None
    budget_remaining_monthly_usd: Decimal | None
    by_provider: list[CostProviderRow]
    top_expensive_jobs: list[ExpensiveJobRow]
    projected_month_end_usd: Decimal
    generated_at: datetime


class WorkerJobRow(BaseModel):
    assignment_id: uuid.UUID
    pipeline_run_id: uuid.UUID
    stage: str
    status: str
    attempt_number: int
    dispatched_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None


class WorkerTimelineRow(BaseModel):
    worker_id: uuid.UUID
    name: str
    status: str
    current_task: str | None
    last_heartbeat_at: datetime | None
    average_execution_seconds: float | None
    failure_percent: float
    retry_percent: float
    jobs: list[WorkerJobRow]


class WorkerTimelineOut(BaseModel):
    workers: list[WorkerTimelineRow]
    generated_at: datetime


class ContentCommandCenterOut(BaseModel):
    ideas: int
    scripts: int
    voiceovers: int
    videos_rendering: int
    ready_for_review: int
    waiting_for_approval: int
    publishing: int
    published: int
    failed: int
    generated_at: datetime


class QuickActionResult(BaseModel):
    action: str
    ok: bool
    affected: int
    message: str
    details: dict = Field(default_factory=dict)


class ExecutiveInsightsOut(BaseModel):
    todays_achievements: list[str]
    todays_failures: list[str]
    highest_risk: str
    suggested_next_action: str
    biggest_cost_today_usd: Decimal
    biggest_cost_today_label: str | None
    most_active_worker: str | None
    most_active_customer: str | None
    generated_at: datetime
