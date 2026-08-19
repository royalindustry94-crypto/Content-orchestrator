"""Publication control closure tests.

Lumora hands content to third-party platforms whose own policies require
synthetic-media disclosure, rights to inputs, and non-repetitive original
output. `app.services.publication_policy.assert_publishable` is the single
gate; these tests prove it is fail-closed for every missing control, that an
approved Human Review Gate is mandatory, and that attestations cannot be
written by a role that is not allowed to certify them.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal, RuntimeSessionLocal
from app.models.content import ContentItem
from app.models.enums import (
    ContentStage,
    ContentStatus,
    PipelineRunStatus,
    ReviewGateStatus,
)
from app.models.pipeline import PipelineRun
from app.models.publication_policy import PublicationEligibility
from app.models.review_gate import ReviewGate
from app.models.workspace import Workspace
from app.models.workspace_membership import WorkspaceMembership, WorkspaceRole
from app.services import publication_policy
from app.services.publication_policy import PublicationBlocked, assert_publishable


async def _seed_workspace(session, *, role: WorkspaceRole = WorkspaceRole.ADMIN):
    user_id = uuid.uuid4()
    email = f"{user_id}@example.com"
    await session.execute(
        text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
        {"id": str(user_id), "email": email},
    )
    await session.execute(
        text(
            "INSERT INTO profiles (id, email) VALUES (:id, :email) "
            "ON CONFLICT (id) DO NOTHING"
        ),
        {"id": str(user_id), "email": email},
    )
    ws = Workspace(id=uuid.uuid4(), name=f"pub-{user_id}", created_by=user_id)
    session.add(ws)
    await session.flush()
    session.add(
        WorkspaceMembership(workspace_id=ws.id, user_id=user_id, role=role)
    )
    await session.flush()
    return ws, user_id


async def _seed_item_and_gate(
    session, ws, user_id, *, gate_status: ReviewGateStatus | None
):
    item = ContentItem(
        id=uuid.uuid4(),
        workspace_id=ws.id,
        topic="publication control probe",
        current_stage=ContentStage.SCRIPTING,
        status=ContentStatus.ACTIVE,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(item)
    await session.flush()

    gate = None
    if gate_status is not None:
        run = PipelineRun(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            content_item_id=item.id,
            current_stage=ContentStage.SCRIPTING,
            status=PipelineRunStatus.RUNNING,
        )
        session.add(run)
        await session.flush()
        gate = ReviewGate(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            pipeline_run_id=run.id,
            stage=ContentStage.SCRIPTING,
            status=gate_status,
            requested_at=datetime.now(UTC),
        )
        session.add(gate)
        await session.flush()
    return item, gate


def _fingerprint(seed: str) -> str:
    return publication_policy.fingerprint_script(f"hook {seed}", f"body {seed}", "cta")


# --- fail-closed behaviour -------------------------------------------------


@pytest.mark.asyncio
async def test_no_eligibility_record_blocks_publication():
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, _ = await _seed_item_and_gate(session, ws, user_id, gate_status=None)
        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="youtube",
            )
        assert exc.value.code == "eligibility_missing"
        await session.rollback()


@pytest.mark.asyncio
async def test_unsupported_platform_is_refused_not_attempted():
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, _ = await _seed_item_and_gate(session, ws, user_id, gate_status=None)
        for platform in ("", "twitter", "linkedin", "YOUTUBE-SHORTS", "unknown"):
            with pytest.raises(PublicationBlocked) as exc:
                await assert_publishable(
                    session,
                    workspace_id=ws.id,
                    content_item_id=item.id,
                    platform=platform,
                )
            assert exc.value.code == "unsupported_platform", platform
        await session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("gate_status", "expected_code"),
    [
        (ReviewGateStatus.AWAITING, "review_gate_not_approved"),
        (ReviewGateStatus.REJECTED, "review_gate_not_approved"),
        (ReviewGateStatus.TIMED_OUT, "review_gate_not_approved"),
    ],
)
async def test_publication_requires_an_approved_review_gate(gate_status, expected_code):
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, gate = await _seed_item_and_gate(
            session, ws, user_id, gate_status=gate_status
        )
        session.add(
            PublicationEligibility(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="tiktok",
                generated_by="lumora-pipeline",
                synthetic_media_disclosed=True,
                rights_confirmed_by=user_id,
                rights_confirmed_at=datetime.now(UTC),
                originality_fingerprint=_fingerprint(str(item.id)),
                review_gate_id=gate.id,
            )
        )
        await session.flush()
        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="tiktok",
            )
        assert exc.value.code == expected_code
        await session.rollback()


@pytest.mark.asyncio
async def test_missing_review_gate_reference_blocks_publication():
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, _ = await _seed_item_and_gate(session, ws, user_id, gate_status=None)
        session.add(
            PublicationEligibility(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="instagram",
                synthetic_media_disclosed=True,
                rights_confirmed_by=user_id,
                rights_confirmed_at=datetime.now(UTC),
                originality_fingerprint=_fingerprint(str(item.id)),
                review_gate_id=None,
            )
        )
        await session.flush()
        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="instagram",
            )
        assert exc.value.code == "review_gate_missing"
        await session.rollback()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ({"synthetic_media_disclosed": False}, "synthetic_media_not_disclosed"),
        (
            {"rights_confirmed_by": None, "rights_confirmed_at": None},
            "rights_not_confirmed",
        ),
        ({"originality_fingerprint": None}, "originality_fingerprint_missing"),
    ],
)
async def test_each_missing_attestation_blocks_publication(mutation, expected_code):
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, gate = await _seed_item_and_gate(
            session, ws, user_id, gate_status=ReviewGateStatus.APPROVED
        )
        fields = {
            "id": uuid.uuid4(),
            "workspace_id": ws.id,
            "content_item_id": item.id,
            "platform": "youtube",
            "generated_by": "lumora-pipeline",
            "synthetic_media_disclosed": True,
            "rights_confirmed_by": user_id,
            "rights_confirmed_at": datetime.now(UTC),
            "originality_fingerprint": _fingerprint(str(item.id)),
            "review_gate_id": gate.id,
        }
        fields.update(mutation)
        session.add(PublicationEligibility(**fields))
        await session.flush()
        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="youtube",
            )
        assert exc.value.code == expected_code
        await session.rollback()


@pytest.mark.asyncio
async def test_repetitive_duplicate_output_is_blocked_per_platform():
    """Two items with identical scripts targeting the same platform: the
    second is refused (mass-produced repetitive content).
    """
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        shared_fingerprint = _fingerprint("identical-script")

        first, gate_a = await _seed_item_and_gate(
            session, ws, user_id, gate_status=ReviewGateStatus.APPROVED
        )
        second, gate_b = await _seed_item_and_gate(
            session, ws, user_id, gate_status=ReviewGateStatus.APPROVED
        )
        for item, gate in ((first, gate_a), (second, gate_b)):
            session.add(
                PublicationEligibility(
                    id=uuid.uuid4(),
                    workspace_id=ws.id,
                    content_item_id=item.id,
                    platform="youtube",
                    generated_by="lumora-pipeline",
                    synthetic_media_disclosed=True,
                    rights_confirmed_by=user_id,
                    rights_confirmed_at=datetime.now(UTC),
                    originality_fingerprint=shared_fingerprint,
                    review_gate_id=gate.id,
                )
            )
        await session.flush()

        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws.id,
                content_item_id=second.id,
                platform="youtube",
            )
        assert exc.value.code == "duplicate_content_for_platform"
        await session.rollback()


@pytest.mark.asyncio
async def test_fully_attested_content_is_publishable():
    async with AsyncSessionLocal() as session:
        ws, user_id = await _seed_workspace(session)
        item, gate = await _seed_item_and_gate(
            session, ws, user_id, gate_status=ReviewGateStatus.APPROVED
        )
        eligibility_id = uuid.uuid4()
        session.add(
            PublicationEligibility(
                id=eligibility_id,
                workspace_id=ws.id,
                content_item_id=item.id,
                platform="youtube",
                generated_by="lumora-pipeline",
                synthetic_media_disclosed=True,
                rights_confirmed_by=user_id,
                rights_confirmed_at=datetime.now(UTC),
                originality_fingerprint=_fingerprint(str(item.id)),
                review_gate_id=gate.id,
            )
        )
        await session.flush()

        decision = await assert_publishable(
            session,
            workspace_id=ws.id,
            content_item_id=item.id,
            platform="YouTube",  # normalisation
        )
        assert decision.platform == "youtube"
        assert decision.eligibility_id == eligibility_id
        assert decision.review_gate_id == gate.id
        await session.rollback()


@pytest.mark.asyncio
async def test_eligibility_from_another_workspace_is_not_usable():
    async with AsyncSessionLocal() as session:
        ws_a, user_a = await _seed_workspace(session)
        ws_b, _user_b = await _seed_workspace(session)
        item, gate = await _seed_item_and_gate(
            session, ws_a, user_a, gate_status=ReviewGateStatus.APPROVED
        )
        session.add(
            PublicationEligibility(
                id=uuid.uuid4(),
                workspace_id=ws_a.id,
                content_item_id=item.id,
                platform="youtube",
                synthetic_media_disclosed=True,
                rights_confirmed_by=user_a,
                rights_confirmed_at=datetime.now(UTC),
                originality_fingerprint=_fingerprint(str(item.id)),
                review_gate_id=gate.id,
            )
        )
        await session.flush()

        # Same item id, but asked for under the other tenant.
        with pytest.raises(PublicationBlocked) as exc:
            await assert_publishable(
                session,
                workspace_id=ws_b.id,
                content_item_id=item.id,
                platform="youtube",
            )
        assert exc.value.code == "eligibility_missing"
        await session.rollback()


def test_fingerprint_is_stable_and_normalised():
    a = publication_policy.fingerprint_script("Hook", "Body", "CTA")
    b = publication_policy.fingerprint_script("  hook ", "body", "cta  ")
    assert a == b
    assert a != publication_policy.fingerprint_script("hook", "different", "cta")
    with pytest.raises(PublicationBlocked) as exc:
        publication_policy.fingerprint_script(None, "", "   ")
    assert exc.value.code == "originality_fingerprint_missing"


# --- attestation write authority (RLS) ------------------------------------


@pytest.mark.asyncio
async def test_editor_cannot_write_a_publication_attestation():
    """Rights/disclosure attestations are compliance statements: only admin or
    reviewer roles may insert them. Enforced by RLS, checked on the runtime
    (RLS-bound) role rather than the owner role.
    """
    async with AsyncSessionLocal() as session:
        ws, editor_id = await _seed_workspace(session, role=WorkspaceRole.EDITOR)
        item, gate = await _seed_item_and_gate(
            session, ws, editor_id, gate_status=ReviewGateStatus.APPROVED
        )
        await session.commit()

    async with RuntimeSessionLocal() as rt:
        await rt.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
            {"sub": str(editor_id)},
        )
        with pytest.raises(Exception) as exc:
            await rt.execute(
                text(
                    "INSERT INTO publication_eligibility "
                    "(workspace_id, content_item_id, platform, "
                    " synthetic_media_disclosed, review_gate_id) "
                    "VALUES (:ws, :item, 'youtube', true, :gate)"
                ),
                {"ws": str(ws.id), "item": str(item.id), "gate": str(gate.id)},
            )
        assert "row-level security" in str(exc.value).lower()
        await rt.rollback()


@pytest.mark.asyncio
async def test_reviewer_can_write_and_other_tenant_cannot_read():
    async with AsyncSessionLocal() as session:
        ws, reviewer_id = await _seed_workspace(session, role=WorkspaceRole.REVIEWER)
        outsider_ws, outsider_id = await _seed_workspace(session)
        item, gate = await _seed_item_and_gate(
            session, ws, reviewer_id, gate_status=ReviewGateStatus.APPROVED
        )
        await session.commit()

    async with RuntimeSessionLocal() as rt:
        await rt.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
            {"sub": str(reviewer_id)},
        )
        await rt.execute(
            text(
                "INSERT INTO publication_eligibility "
                "(workspace_id, content_item_id, platform, "
                " synthetic_media_disclosed, rights_confirmed_by, "
                " rights_confirmed_at, originality_fingerprint, review_gate_id) "
                "VALUES (:ws, :item, 'tiktok', true, :rid, now(), :fp, :gate)"
            ),
            {
                "ws": str(ws.id),
                "item": str(item.id),
                "rid": str(reviewer_id),
                "fp": _fingerprint(str(item.id)),
                "gate": str(gate.id),
            },
        )
        await rt.commit()

    async with RuntimeSessionLocal() as rt:
        await rt.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
            {"sub": str(outsider_id)},
        )
        visible = (
            await rt.execute(
                text(
                    "SELECT count(*) FROM publication_eligibility "
                    "WHERE workspace_id = :ws"
                ),
                {"ws": str(ws.id)},
            )
        ).scalar_one()
        assert visible == 0, "attestations must not be readable across tenants"
        assert outsider_ws.id != ws.id
