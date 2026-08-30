"""Strict Producer and Media QA V1 API contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductionRunCreate(BaseModel):
    content_package_id: UUID
    target_platform: str | None = Field(default=None, max_length=80)
    target_format: str | None = Field(default=None, max_length=80)
    target_duration_seconds: int | None = Field(default=None, ge=1, le=14_400)
    max_provider_calls: int = Field(default=5, ge=0, le=20)
    max_render_calls: int = Field(default=2, ge=0, le=8)
    max_cost_usd: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("500"))
    max_attempts: int = Field(default=3, ge=1, le=8)
    max_repair_cycles: int = Field(default=2, ge=0, le=5)
    timeout_seconds: int = Field(default=900, ge=30, le=14_400)


class ProductionRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    content_package_id: UUID
    content_item_id: UUID
    content_version_id: UUID
    status: str
    provider_state: str
    target_platform: str | None
    target_format: str | None
    target_duration_seconds: int | None
    max_provider_calls: int
    max_render_calls: int
    max_cost_usd: Decimal
    max_attempts: int
    max_repair_cycles: int
    provider_calls_used: int
    render_calls_used: int
    repair_cycles_used: int
    actual_cost_usd: Decimal
    retry_count: int
    last_error: str | None
    created_at: datetime
    updated_at: datetime


class ProductionAssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    asset_id: UUID
    asset_type: str
    provider: str
    provider_job_id: str | None
    file_hash: str | None
    duration_seconds: Decimal | None
    dimensions: dict
    cost_usd: Decimal
    status: str
    created_at: datetime


class FinalArtifactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_job_id: UUID
    content_version_id: UUID
    render_provider: str
    render_job_id: str | None
    artifact_hash: str
    duration_seconds: Decimal | None
    resolution: dict
    aspect_ratio: str | None
    container: str | None
    codec: str | None
    cost_usd: Decimal
    status: str
    created_at: datetime


class MediaQaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    final_artifact_id: UUID
    artifact_hash: str
    auditor_worker_id: str
    status: str
    checks_run: list
    visual_findings: list
    audio_findings: list
    subtitle_findings: list
    script_alignment: dict
    platform_check: dict
    package_alignment: dict
    evidence: list
    recommended_repair: list
    cost_usd: Decimal
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class ProductionRepairOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    production_job_id: UUID
    final_artifact_id: UUID | None
    media_qa_result_id: UUID | None
    affected_component: str
    repair_operation: str
    repair_cycle: int
    status: str
    cost_usd: Decimal
    provider_calls_used: int
    created_at: datetime


class ProductionReadinessOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    final_artifact_id: UUID
    content_version_id: UUID
    media_qa_state: str
    compliance_state: str
    chief_audit_state: str
    human_review_state: str
    status: str
    blocking_reasons: list
    total_cost_usd: Decimal
    updated_at: datetime


class ProductionSummaryOut(BaseModel):
    provider_state: str
    production_jobs: int
    active_jobs: int
    final_artifacts: int
    media_qa_passed: int
    media_qa_blocked: int
    repair_required: int
    compliance_ready: int
    provider_cost_usd: Decimal
    last_error: str | None
    real_provider_mode: bool
    test_fixture_mode: bool


class ProductionDetailOut(BaseModel):
    job: ProductionRunOut
    assets: list[ProductionAssetOut]
    artifacts: list[FinalArtifactOut]
    media_qa: list[MediaQaOut]
    repairs: list[ProductionRepairOut]
    readiness: list[ProductionReadinessOut]
