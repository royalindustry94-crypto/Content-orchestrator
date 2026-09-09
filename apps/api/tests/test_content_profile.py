"""Workspace content profile: the onboarding-setup persistence surface
(migration 0055). Covers the honest-null-until-saved contract, the
upsert/full-replace semantics, role gating (editor/admin write, reviewer
read-only), and cross-workspace isolation.
"""

import uuid as _uuid

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from tests.conftest import make_token


async def _register_user(user_id: str) -> None:
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT DO NOTHING"),
            {"id": user_id, "email": f"{user_id}@test.example"},
        )
        await session.commit()


async def _create_workspace(client, headers, name="Acme"):
    response = await client.post("/workspaces", json={"name": name}, headers=headers)
    assert response.status_code == 201
    return response.json()["id"]


async def _add_member(client, admin_headers, workspace_id, role):
    member_id = str(_uuid.uuid4())
    await _register_user(member_id)
    token = make_token(user_id=member_id)
    headers = {"Authorization": f"Bearer {token}"}
    invite = await client.post(
        f"/workspaces/{workspace_id}/memberships",
        json={"user_id": member_id, "role": role},
        headers=admin_headers,
    )
    assert invite.status_code == 201
    return member_id, headers


@pytest.mark.asyncio
async def test_profile_is_null_until_saved(client, new_user):
    _, _, headers = new_user
    workspace_id = await _create_workspace(client, headers)

    response = await client.get(f"/workspaces/{workspace_id}/content-profile", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_save_then_read_round_trips(client, new_user):
    _, _, headers = new_user
    workspace_id = await _create_workspace(client, headers)

    payload = {
        "business_name": "Acme Studio",
        "offer": "Short-form video for local restaurants",
        "target_audience": "  Restaurant owners in mid-size US cities  ",
        "brand_voice": "Warm, direct, a little playful",
        "target_platform": "instagram",
        "content_goal": "book more tastings",
    }
    saved = await client.put(
        f"/workspaces/{workspace_id}/content-profile", json=payload, headers=headers
    )
    assert saved.status_code == 200
    body = saved.json()
    assert body["business_name"] == "Acme Studio"
    # Whitespace-only padding is stripped server-side, not stored verbatim.
    assert body["target_audience"] == "Restaurant owners in mid-size US cities"
    assert body["is_complete"] is True

    fetched = await client.get(f"/workspaces/{workspace_id}/content-profile", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["business_name"] == "Acme Studio"


@pytest.mark.asyncio
async def test_partial_profile_is_not_complete(client, new_user):
    _, _, headers = new_user
    workspace_id = await _create_workspace(client, headers)

    saved = await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Acme Studio"},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["is_complete"] is False
    assert saved.json()["offer"] is None


@pytest.mark.asyncio
async def test_second_save_fully_replaces_not_merges(client, new_user):
    """A field omitted in a later PUT is cleared, not left stale — the
    caller always sends the full current form state (matches how the
    wizard and the Settings form both work: one full-object submit).
    """
    _, _, headers = new_user
    workspace_id = await _create_workspace(client, headers)

    await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Acme Studio", "offer": "Video production"},
        headers=headers,
    )
    second = await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Acme Studio Rebrand"},
        headers=headers,
    )
    assert second.status_code == 200
    body = second.json()
    assert body["business_name"] == "Acme Studio Rebrand"
    assert body["offer"] is None


@pytest.mark.asyncio
async def test_reviewer_can_read_but_not_write(client, new_user):
    admin_id, _, admin_headers = new_user
    workspace_id = await _create_workspace(client, admin_headers)
    _, reviewer_headers = await _add_member(client, admin_headers, workspace_id, "reviewer")

    write = await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Nope"},
        headers=reviewer_headers,
    )
    assert write.status_code == 403

    read = await client.get(f"/workspaces/{workspace_id}/content-profile", headers=reviewer_headers)
    assert read.status_code == 200


@pytest.mark.asyncio
async def test_editor_can_write(client, new_user):
    admin_id, _, admin_headers = new_user
    workspace_id = await _create_workspace(client, admin_headers)
    _, editor_headers = await _add_member(client, admin_headers, workspace_id, "editor")

    write = await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Editor Wrote This"},
        headers=editor_headers,
    )
    assert write.status_code == 200
    assert write.json()["business_name"] == "Editor Wrote This"


@pytest.mark.asyncio
async def test_non_member_cannot_read_or_write(client, new_user):
    _, _, owner_headers = new_user
    workspace_id = await _create_workspace(client, owner_headers)

    outsider_token = make_token()
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}

    read = await client.get(f"/workspaces/{workspace_id}/content-profile", headers=outsider_headers)
    assert read.status_code == 403
    write = await client.put(
        f"/workspaces/{workspace_id}/content-profile",
        json={"business_name": "Nope"},
        headers=outsider_headers,
    )
    assert write.status_code == 403


@pytest.mark.asyncio
async def test_profiles_are_isolated_per_workspace(client, new_user):
    _, _, headers = new_user
    ws_a = await _create_workspace(client, headers, name="Workspace A")
    ws_b = await _create_workspace(client, headers, name="Workspace B")

    await client.put(
        f"/workspaces/{ws_a}/content-profile",
        json={"business_name": "A's business"},
        headers=headers,
    )

    b_profile = await client.get(f"/workspaces/{ws_b}/content-profile", headers=headers)
    assert b_profile.status_code == 200
    assert b_profile.json() is None
