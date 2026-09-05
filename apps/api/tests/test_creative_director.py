from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select, text

from app.core.security import rls_scoped_session
from app.db.session import AsyncSessionLocal
from app.models.creative_director import (
    CreativeBriefVersion,
    CreativeProject,
    PromptPackDecision,
    PromptPackVersion,
)
from tests.conftest import make_token


async def _register_user(user_id: uuid.UUID) -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email)"),
            {"id": str(user_id), "email": f"{user_id}@example.com"},
        )
        await session.commit()
    return {"Authorization": f"Bearer {make_token(user_id=str(user_id))}"}


async def _workspace(client, headers: dict[str, str], name: str) -> str:
    response = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _project_payload() -> dict:
    return {
        "title": "Rescue plumber cartoon",
        "desired_outcome": "A clear 20-second advert with no costly continuity rework",
        "brief": {
            "customer_request": "Make a funny cartoon plumber rescue a flooded kitchen.",
            "requirements": {
                "platform": "short-form video",
                "duration_seconds": 20,
                "style": "warm 3D cartoon",
                "audience": "local homeowners",
            },
            "exclusions": ["unreadable text", "changing uniform colours"],
            "reference_notes": "The plumber wears navy overalls in every scene.",
        },
    }


def _pack_payload(brief_id: str, *, scene: str = "wide kitchen shot") -> dict:
    return {
        "brief_version_id": brief_id,
        "target_tool": "customer-selected generator",
        "prompt_spec": {
            "scenes": [
                {
                    "number": 1,
                    "visual": scene,
                    "camera": "slow push-in",
                    "dialogue": "We will stop that leak.",
                }
            ]
        },
        "continuity_rules": ["navy overalls", "same red toolbox"],
        "negative_prompts": ["extra fingers", "unreadable lettering"],
        "validation_checklist": ["character matches reference", "spoken price is correct"],
        "estimated_generation_count": 2,
    }


@pytest.mark.asyncio
async def test_exact_prompt_pack_must_be_human_approved_before_generation(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _workspace(client, headers, "Creative approval")

    created = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects",
        json=_project_payload(),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project = created.json()
    project_id = project["project"]["id"]
    brief_id = project["latest_brief"]["id"]
    assert len(project["latest_brief"]["fingerprint"]) == 64
    assert project["approved_for_generation"] is False

    packed = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/prompt-packs",
        json=_pack_payload(brief_id),
        headers=headers,
    )
    assert packed.status_code == 201, packed.text
    pack = packed.json()
    assert len(pack["fingerprint"]) == 64

    wrong = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}"
        f"/prompt-packs/{pack['id']}/decision",
        json={"approved": True, "prompt_pack_fingerprint": "0" * 64},
        headers=headers,
    )
    assert wrong.status_code == 409
    assert "fingerprint" in wrong.json()["detail"]

    approved = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}"
        f"/prompt-packs/{pack['id']}/decision",
        json={
            "approved": True,
            "prompt_pack_fingerprint": pack["fingerprint"],
            "notes": "Storyboard and continuity rules checked",
        },
        headers=headers,
    )
    assert approved.status_code == 201, approved.text
    assert approved.json()["decision"] == "approved"

    detail = await client.get(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}",
        headers=headers,
    )
    assert detail.status_code == 200
    assert detail.json()["approved_for_generation"] is True
    assert detail.json()["latest_decision"]["prompt_pack_fingerprint"] == pack["fingerprint"]

    newer = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/prompt-packs",
        json=_pack_payload(brief_id, scene="corrected kitchen establishing shot"),
        headers=headers,
    )
    assert newer.status_code == 201, newer.text
    assert newer.json()["fingerprint"] != pack["fingerprint"]

    invalidated = await client.get(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}",
        headers=headers,
    )
    assert invalidated.status_code == 200
    assert invalidated.json()["approved_for_generation"] is False

    stale = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}"
        f"/prompt-packs/{pack['id']}/decision",
        json={"approved": True, "prompt_pack_fingerprint": pack["fingerprint"]},
        headers=headers,
    )
    assert stale.status_code == 409
    assert "latest" in stale.json()["detail"]


@pytest.mark.asyncio
async def test_new_brief_invalidates_old_prompt_input(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _workspace(client, headers, "Brief revision")
    created = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects",
        json=_project_payload(),
        headers=headers,
    )
    project_id = created.json()["project"]["id"]
    old_brief_id = created.json()["latest_brief"]["id"]

    revised = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/brief-versions",
        json={
            "customer_request": "Make the plumber an adult woman and remove all dialogue.",
            "requirements": {"duration_seconds": 15, "format": "vertical"},
            "exclusions": ["dialogue"],
        },
        headers=headers,
    )
    assert revised.status_code == 201, revised.text
    assert revised.json()["revision_number"] == 2

    stale_pack = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/prompt-packs",
        json=_pack_payload(old_brief_id),
        headers=headers,
    )
    assert stale_pack.status_code == 409
    assert "latest creative brief" in stale_pack.json()["detail"]


@pytest.mark.asyncio
async def test_roles_and_workspace_isolation_are_fail_closed(client, new_user):
    _admin_id, _token, admin_headers = new_user
    workspace_id = await _workspace(client, admin_headers, "Creative tenant A")
    created = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects",
        json=_project_payload(),
        headers=admin_headers,
    )
    project_id = created.json()["project"]["id"]
    brief_id = created.json()["latest_brief"]["id"]

    outsider_id = uuid.uuid4()
    outsider_headers = await _register_user(outsider_id)
    outsider = await client.get(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}",
        headers=outsider_headers,
    )
    assert outsider.status_code == 403

    other_workspace = await _workspace(client, outsider_headers, "Creative tenant B")
    cross_workspace = await client.get(
        f"/workspaces/{other_workspace}/creative-director/projects/{project_id}",
        headers=outsider_headers,
    )
    assert cross_workspace.status_code == 404

    reviewer_id = uuid.uuid4()
    reviewer_headers = await _register_user(reviewer_id)
    invited = await client.post(
        f"/workspaces/{workspace_id}/memberships",
        json={"user_id": str(reviewer_id), "role": "reviewer"},
        headers=admin_headers,
    )
    assert invited.status_code == 201

    forbidden_create = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/prompt-packs",
        json=_pack_payload(brief_id),
        headers=reviewer_headers,
    )
    assert forbidden_create.status_code == 403

    packed = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}/prompt-packs",
        json=_pack_payload(brief_id),
        headers=admin_headers,
    )
    pack = packed.json()
    reviewed = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects/{project_id}"
        f"/prompt-packs/{pack['id']}/decision",
        json={"approved": False, "prompt_pack_fingerprint": pack["fingerprint"]},
        headers=reviewer_headers,
    )
    assert reviewed.status_code == 201, reviewed.text
    assert reviewed.json()["decision"] == "changes_requested"

    async with rls_scoped_session(str(outsider_id)) as session:
        assert (
            await session.scalar(
                select(CreativeProject.id).where(CreativeProject.workspace_id == workspace_id)
            )
            is None
        )
        assert (
            await session.scalar(
                select(CreativeBriefVersion.id).where(
                    CreativeBriefVersion.workspace_id == workspace_id
                )
            )
            is None
        )
        assert (
            await session.scalar(
                select(PromptPackVersion.id).where(PromptPackVersion.workspace_id == workspace_id)
            )
            is None
        )
        assert (
            await session.scalar(
                select(PromptPackDecision.id).where(
                    PromptPackDecision.workspace_id == workspace_id
                )
            )
            is None
        )


@pytest.mark.asyncio
async def test_creative_tables_force_rls_and_versions_are_immutable(client, new_user):
    _user_id, _token, headers = new_user
    workspace_id = await _workspace(client, headers, "Creative schema controls")
    created = await client.post(
        f"/workspaces/{workspace_id}/creative-director/projects",
        json=_project_payload(),
        headers=headers,
    )
    assert created.status_code == 201, created.text
    brief_id = created.json()["latest_brief"]["id"]

    async with AsyncSessionLocal() as session:
        rows = await session.execute(
            text(
                "SELECT relname, relrowsecurity, relforcerowsecurity "
                "FROM pg_class WHERE relname IN ("
                "'creative_projects','creative_brief_versions',"
                "'prompt_pack_versions','prompt_pack_decisions')"
            )
        )
        controls = {row[0]: (row[1], row[2]) for row in rows}
        assert controls == {
            "creative_projects": (True, True),
            "creative_brief_versions": (True, True),
            "prompt_pack_versions": (True, True),
            "prompt_pack_decisions": (True, True),
        }

        with pytest.raises(Exception) as exc_info:
            await session.execute(
                text(
                    "UPDATE creative_brief_versions "
                    "SET customer_request = 'silently changed' WHERE id = :id"
                ),
                {"id": brief_id},
            )
        assert "immutable" in str(exc_info.value).lower()
        await session.rollback()
