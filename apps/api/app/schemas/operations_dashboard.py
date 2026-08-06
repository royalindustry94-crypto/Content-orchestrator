"""Read-only Operations Dashboard API contracts (V1 + V2 Founder Control Center)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
    current_task: str | None
    queue: int
    last_heartbeat_at: datetime | None
    retry_count: int
    jobs_completed: int
    jobs_failed: int
    jobs_completed_today: int
    jobs_failed_today: int
    cpu_percent: float | None
    memory_percent: float | None
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
    jobs_completed: int
    jobs_waiting: int
    jobs_failed: int
    human_reviews_waiting: int
    publishing_queue: int
    pipelines: list[PipelineRow]
    generated_at: datetime


class OperationsAlert(BaseModel):
    key: str
    severity: str
    title: str
    count: int
    message: str
    occurred_at: datetime | None = None


class AlertsOut(BaseModel):
    alerts: list[OperationsAlert]
    generated_at: datetime


class NotificationsOut(BaseModel):
    notifications: list[OperationsAlert]
    generated_at: datetime


class LeadOut(BaseModel):
    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    company: str | None
    email: str
    source: str
    status: str
    notes: str | None
    follow_up_date: date | None
    created_at: datetime
    updated_at: datetime


class LeadCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    email: str = Field(min_length=3, max_length=320)
    source: str = Field(default="manual", min_length=1, max_length=100)
    status: str = Field(default="new", min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=4000)
    follow_up_date: date | None = None


class LeadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, min_length=3, max_length=320)
    source: str | None = Field(default=None, min_length=1, max_length=100)
    status: str | None = Field(default=None, min_length=1, max_length=32)
    notes: str | None = Field(default=None, max_length=4000)
    follow_up_date: date | None = None


class LeadsOut(BaseModel):
    leads: list[LeadOut]
    total: int
    generated_at: datetime


class CustomerRow(BaseModel):
    workspace_id: uuid.UUID
    name: str
    plan: str
    subscription_status: str
    member_count: int
    stripe_customer_id: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    created_at: datetime


class CustomersOut(BaseModel):
    beta_users: int
    active_users: int
    paying_users: int
    trial_users: int
    revenue_mtd_usd: Decimal
    revenue_source: str
    customers: list[CustomerRow]
    generated_at: datetime


class SpendProviderRow(BaseModel):
    provider: str
    today_usd: Decimal
    week_usd: Decimal
    month_usd: Decimal


class SpendOut(BaseModel):
    today_usd: Decimal
    week_usd: Decimal
    month_usd: Decimal
    by_provider: list[SpendProviderRow]
    daily_cap_usd: Decimal | None
    monthly_cap_usd: Decimal | None
    budget_remaining_daily_usd: Decimal | None
    budget_remaining_monthly_usd: Decimal | None
    generated_at: datetime


class GitHubCommit(BaseModel):
    sha: str
    message: str
    author: str | None
    committed_at: datetime | None
    url: str | None


class GitHubPullRequest(BaseModel):
    number: int
    title: str
    state: str
    author: str | None
    updated_at: datetime | None
    url: str | None


class GitHubActionRun(BaseModel):
    id: int
    name: str
    status: str
    conclusion: str | None
    branch: str | None
    updated_at: datetime | None
    url: str | None


class GitHubBranchStatus(BaseModel):
    name: str | None
    sha: str | None
    protected: bool | None
    ci_status: str


class GitHubOut(BaseModel):
    available: bool
    unavailable_reason: str | None
    repository: str | None
    latest_commits: list[GitHubCommit]
    open_pull_requests: list[GitHubPullRequest]
    failed_actions: list[GitHubActionRun]
    branch_status: GitHubBranchStatus
    generated_at: datetime
