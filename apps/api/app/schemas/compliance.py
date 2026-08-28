from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ComplianceRunRequest(BaseModel):
    final_artifact_id: UUID
    target_platform: str = Field(min_length=2, max_length=64)
    max_provider_calls: int = Field(default=5, ge=0, le=5)
    max_verification_calls: int = Field(default=5, ge=0, le=5)
    max_tokens: int = Field(default=4000, ge=0, le=4000)
    max_cost_usd: Decimal = Field(default=Decimal("0.00"), ge=0, le=Decimal("0.00"))
    max_attempts: int = Field(default=3, ge=1, le=3)


class PolicySourceInput(BaseModel):
    platform: str = Field(min_length=2, max_length=64)
    policy_category: str = Field(min_length=2, max_length=128)
    source: str = Field(min_length=2, max_length=128)
    source_reference: HttpUrl
    rule_version: str = Field(min_length=1, max_length=128)


class ComplianceSummaryResponse(BaseModel):
    provider_state: str
    policy_state: str
    compliance_audits: int
    passed: int
    blocked: int
    human_review_packages: int
    publication_eligible: int
    provider_cost_usd: Decimal
    real_provider_mode: bool
    test_fixture_mode: bool


class ComplianceAuditResponse(BaseModel):
    id: UUID
    final_artifact_id: UUID
    artifact_hash: str
    content_version_id: UUID
    target_platform: str
    status: str
    risk_level: str
    rights_status: str
    provider_state: str
    findings: list
    required_disclosures: list
    cost_usd: Decimal
    test_data: bool


class ChiefAuditResponse(BaseModel):
    id: UUID
    final_artifact_id: UUID
    artifact_hash: str
    status: str
    lineage_status: str
    version_integrity_status: str
    cost_reconciliation_status: str
    provider_reconciliation_status: str
    blockers: list
    test_data: bool


class HumanReviewPackageResponse(BaseModel):
    id: UUID
    final_artifact_id: UUID
    artifact_hash: str
    content_version_id: UUID
    target_platform: str
    review_gate_id: UUID | None
    warnings: list
    required_disclosures: list
    total_cost_usd: Decimal
    test_data: bool


class ArtifactPublicationEligibilityResponse(BaseModel):
    id: UUID
    final_artifact_id: UUID
    artifact_hash: str
    target_platform: str
    status: str
    publication_eligible: bool
    blocking_reasons: list
    test_data: bool


class RecordPolicySourceRequest(PolicySourceInput):
    @field_validator("source_reference")
    @classmethod
    def public_only(cls, value: HttpUrl) -> HttpUrl:
        host = value.host or ""
        if host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".local"):
            raise ValueError("policy source must use a public reference")
        return value
