"""Mission Control V4 contracts."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.schemas.operations_mission import ActivityItem, HealthIndicator


class SearchResult(BaseModel):
    type: str
    id: str
    title: str
    subtitle: str | None
    status: str | None
    occurred_at: datetime | None
    url: str | None = None


class GlobalSearchOut(BaseModel):
    query: str
    results: list[SearchResult]
    total: int
    generated_at: datetime


class UniversalTimelineOut(BaseModel):
    items: list[ActivityItem]
    generated_at: datetime


class WorkerLogOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    worker_id: uuid.UUID
    worker_name: str
    pipeline_run_id: uuid.UUID | None
    assignment_id: uuid.UUID | None
    severity: str
    message: str
    context: dict
    occurred_at: datetime
    received_at: datetime


class LiveLogsOut(BaseModel):
    logs: list[WorkerLogOut]
    generated_at: datetime


class ExecutiveModeOut(BaseModel):
    health: list[HealthIndicator]
    revenue_mtd_usd: Decimal
    spend_today_usd: Decimal
    spend_month_usd: Decimal
    workers_online: int
    workers_total: int
    jobs_running: int
    jobs_waiting: int
    jobs_failed_today: int
    critical_alerts: int
    reviews_waiting: int
    new_customers_today: int
    todays_summary: list[str]
    generated_at: datetime


class AssistantQuestionIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class AssistantAnswerOut(BaseModel):
    question: str
    intent: str
    answer: str
    facts: list[dict]
    generated_at: datetime
