import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text

from app.core.security import rls_scoped_session
from app.db.session import AsyncSessionLocal
from app.models.compliance import ArtifactPublicationEligibility, ComplianceAudit
from app.schemas.compliance import ComplianceRunRequest
from app.services import compliance, production
from tests.test_production_v1 import _audited_package
from tests.test_strategy_v1 import _tenant


async def _artifact(user_id: uuid.UUID, workspace_id: uuid.UUID):
    package = await _audited_package(user_id, workspace_id)
    async with rls_scoped_session(str(user_id)) as session:
        job = await production.create_production_run(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            content_package_id=package.id,
            target_platform="short_video",
            target_format="mp4",
            target_duration_seconds=30,
            max_provider_calls=1,
            max_render_calls=1,
            max_cost_usd=Decimal("0"),
            max_attempts=1,
            max_repair_cycles=1,
            timeout_seconds=300,
        )
        job.test_data = True
        artifact = await production.create_test_fixture_artifact(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            production_job_id=job.id,
            artifact_hash=production.fixture_hash(f"compliance-{workspace_id}"),
        )
        await production.create_test_media_qa(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
            auditor_worker_id="media-qa-fixture",
            producer_worker_id="producer-fixture",
            status="pass",
        )
        return artifact


@pytest.mark.asyncio
async def test_compliance_run_is_truthful_when_provider_is_not_configured(client, new_user):
    user_id, headers, workspace_id = await _tenant(client, new_user, "Compliance no provider")
    artifact = await _artifact(user_id, workspace_id)
    response = await client.post(
        f"/workspaces/{workspace_id}/compliance/runs",
        headers=headers,
        json={"final_artifact_id": str(artifact.id), "target_platform": "short_video"},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "blocked_provider_not_configured"
    assert body["provider_state"] == "not_configured"
    assert body["cost_usd"] in (0, 0.0, "0", "0.0000")


@pytest.mark.asyncio
async def test_chief_audit_requires_hash_bound_media_qa_and_compliance(client, new_user):
    user_id, _headers, workspace_id = await _tenant(client, new_user, "Chief exact hash")
    artifact = await _artifact(user_id, workspace_id)
    async with rls_scoped_session(str(user_id)) as session:
        blocked = await compliance.run_test_chief_audit(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
        )
        assert blocked.status == "blocked"
        assert "compliance_missing_or_not_pass" in blocked.blockers
        passed = await compliance.create_test_compliance_pass(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
        )
        assert passed.artifact_hash == artifact.artifact_hash
        chief = await compliance.run_test_chief_audit(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
        )
        assert chief.status == "pass_to_human_review"
        assert chief.artifact_hash == artifact.artifact_hash


@pytest.mark.asyncio
async def test_compliance_invalidation_and_external_publication_block(client, new_user):
    user_id, _headers, workspace_id = await _tenant(client, new_user, "Compliance invalidation")
    artifact = await _artifact(user_id, workspace_id)
    async with rls_scoped_session(str(user_id)) as session:
        audit = await compliance.create_test_compliance_pass(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
        )
        invalidation = await compliance.invalidate_compliance(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            compliance_audit_id=audit.id,
            reason="material metadata changed",
        )
        assert invalidation.final_artifact_id == artifact.id
        eligibility = await compliance.publication_eligibility(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
            target_platform="short_video",
        )
        assert eligibility.publication_eligible is False
        assert "external_publishing_disabled" in eligibility.blocking_reasons


@pytest.mark.asyncio
async def test_publication_eligibility_is_idempotent_per_artifact_and_platform(client, new_user):
    """Asking twice must restate the verdict, not raise.

    The table is uniquely constrained on (workspace, artifact, platform), so an
    unconditional insert made a second request fail with a 500 — reachable by a
    repeated request or a double tap, and on the documented walkthrough where
    eligibility is checked both before and after the review decision.
    """
    user_id, _headers, workspace_id = await _tenant(client, new_user, "Eligibility idempotency")
    artifact = await _artifact(user_id, workspace_id)

    async with rls_scoped_session(str(user_id)) as session:
        first = await compliance.publication_eligibility(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
            target_platform="short_video",
        )
        first_id = first.id

    async with rls_scoped_session(str(user_id)) as session:
        second = await compliance.publication_eligibility(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
            target_platform="short_video",
        )
        # Same determination refreshed in place, and still fail-closed.
        assert second.id == first_id
        assert second.publication_eligible is False
        assert "external_publishing_disabled" in second.blocking_reasons

    async with rls_scoped_session(str(user_id)) as session:
        rows = (
            (
                await session.execute(
                    select(ArtifactPublicationEligibility).where(
                        ArtifactPublicationEligibility.workspace_id == workspace_id,
                        ArtifactPublicationEligibility.final_artifact_id == artifact.id,
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    # A different platform is a separate determination, not a refresh.
    async with rls_scoped_session(str(user_id)) as session:
        other = await compliance.publication_eligibility(
            session,
            workspace_id=workspace_id,
            actor_id=user_id,
            final_artifact_id=artifact.id,
            target_platform="youtube_shorts",
        )
        assert other.id != first_id
        assert other.publication_eligible is False


@pytest.mark.asyncio
async def test_compliance_records_are_hidden_by_direct_rls(client, new_user):
    user_id, headers, workspace_id = await _tenant(client, new_user, "Compliance isolation")
    artifact = await _artifact(user_id, workspace_id)
    response = await client.post(
        f"/workspaces/{workspace_id}/compliance/runs",
        headers=headers,
        json={"final_artifact_id": str(artifact.id), "target_platform": "short_video"},
    )
    assert response.status_code == 201
    audit_id = uuid.UUID(response.json()["id"])
    outsider_id = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(outsider_id), "email": f"{outsider_id}@example.com"},
        )
        await session.commit()
    async with rls_scoped_session(str(outsider_id)) as session:
        assert (
            await session.scalar(select(ComplianceAudit.id).where(ComplianceAudit.id == audit_id))
            is None
        )


def test_compliance_limits_are_strict():
    with pytest.raises(ValidationError):
        ComplianceRunRequest(
            final_artifact_id=uuid.uuid4(), target_platform="x", max_provider_calls=6
        )
    with pytest.raises(ValidationError):
        ComplianceRunRequest(final_artifact_id=uuid.uuid4(), target_platform="x", max_tokens=4001)
