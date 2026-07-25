import uuid as _uuid

import pytest
from sqlalchemy import text

from app.db.session import AsyncSessionLocal
from tests.conftest import make_token


async def _register_user(user_id: str) -> None:
    """Insert into auth.users so the profile trigger fires and the
    workspace_memberships FK (→ profiles) can be satisfied.
    """
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :email) ON CONFLICT DO NOTHING"),
            {"id": user_id, "email": f"{user_id}@test.example"},
        )
        await session.commit()


@pytest.mark.asyncio
async def test_create_workspace_makes_creator_sole_admin(client, new_user):
    _, _, headers = new_user

    response = await client.post("/workspaces", json={"name": "Acme Pillar"}, headers=headers)
    assert response.status_code == 201
    workspace_id = response.json()["id"]

    members = await client.get(f"/workspaces/{workspace_id}/memberships", headers=headers)
    assert members.status_code == 200
    roles = [m["role"] for m in members.json()]
    assert roles == ["admin"]


@pytest.mark.asyncio
async def test_non_member_cannot_view_workspace(client, new_user):
    _, _, owner_headers = new_user
    create = await client.post("/workspaces", json={"name": "Private"}, headers=owner_headers)
    workspace_id = create.json()["id"]

    outsider_token = make_token()
    outsider_headers = {"Authorization": f"Bearer {outsider_token}"}
    # Outsider has a valid JWT but was never created via auth.users / has
    # no membership — the app guard should 403 before RLS is reached.
    response = await client.get(f"/workspaces/{workspace_id}", headers=outsider_headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_editor_and_reviewer_cannot_invite_members(client, new_user):
    admin_id, _, admin_headers = new_user
    create = await client.post("/workspaces", json={"name": "Team"}, headers=admin_headers)
    workspace_id = create.json()["id"]

    for role in ("editor", "reviewer"):
        member_id = str(_uuid.uuid4())
        await _register_user(member_id)
        member_token = make_token(user_id=member_id)
        member_headers = {"Authorization": f"Bearer {member_token}"}

        # Admin adds them at the given role first.
        add = await client.post(
            f"/workspaces/{workspace_id}/memberships",
            json={"user_id": member_id, "role": role},
            headers=admin_headers,
        )
        assert add.status_code == 201

        # That member tries to invite someone else — must be forbidden.
        another_id = str(_uuid.uuid4())
        attempt = await client.post(
            f"/workspaces/{workspace_id}/memberships",
            json={"user_id": another_id, "role": "editor"},
            headers=member_headers,
        )
        assert attempt.status_code == 403


@pytest.mark.asyncio
async def test_member_can_leave_but_not_remove_others(client, new_user):
    import uuid as _uuid

    admin_id, _, admin_headers = new_user
    create = await client.post("/workspaces", json={"name": "Leave Test"}, headers=admin_headers)
    workspace_id = create.json()["id"]

    editor_id = str(_uuid.uuid4())
    await _register_user(editor_id)
    editor_token = make_token(user_id=editor_id)
    editor_headers = {"Authorization": f"Bearer {editor_token}"}
    await client.post(
        f"/workspaces/{workspace_id}/memberships",
        json={"user_id": editor_id, "role": "editor"},
        headers=admin_headers,
    )

    # Editor cannot remove the admin.
    forbidden = await client.delete(
        f"/workspaces/{workspace_id}/memberships/{admin_id}", headers=editor_headers
    )
    assert forbidden.status_code == 403

    # Editor can remove themselves.
    ok = await client.delete(
        f"/workspaces/{workspace_id}/memberships/{editor_id}", headers=editor_headers
    )
    assert ok.status_code == 204

    # Verify the row is actually gone from the DB (not silently blocked by RLS).
    from sqlalchemy import select as _select

    from app.db.session import AsyncSessionLocal
    from app.models.workspace_membership import WorkspaceMembership as WM
    async with AsyncSessionLocal() as _s:
        _row = await _s.execute(
            _select(WM).where(WM.workspace_id == workspace_id, WM.user_id == editor_id)
        )
        assert _row.scalar_one_or_none() is None, (
            "self-leave DELETE was silently suppressed by RLS — membership row still exists"
        )


@pytest.mark.asyncio
async def test_last_admin_cannot_be_removed(client, new_user):
    admin_id, _, admin_headers = new_user
    create = await client.post("/workspaces", json={"name": "Solo Admin"}, headers=admin_headers)
    workspace_id = create.json()["id"]

    response = await client.delete(
        f"/workspaces/{workspace_id}/memberships/{admin_id}", headers=admin_headers
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_invalid_token_is_401_not_403_or_500(client):
    response = await client.get(
        "/workspaces", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_missing_profile_self_heals_on_get_me(client):
    """A verified JWT for a user whose profile row doesn't exist yet
    (e.g. trigger hasn't run, or predates the trigger) should self-heal,
    not 500. This deliberately mints a token WITHOUT inserting into
    auth.users first, so no trigger has fired.
    """
    token = make_token()
    response = await client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"]
