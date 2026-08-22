"""P0: local email/password auth minting Supabase-shaped JWTs."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_signup_login_and_create_workspace(client):
    import uuid

    # Unique per run: a fixed address made this test depend on whatever
    # password a previous run stored on the shared database.
    email = f"beta.user-{uuid.uuid4().hex[:10]}@example.com"
    # Meets the M-F minimum length policy (local_auth.MIN_PASSWORD_LENGTH).
    password = "securepass1-beta"
    signup = await client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": "Beta User"},
    )
    assert signup.status_code == 201, signup.text
    assert signup.json()["email"] == email

    login = await client.post(
        "/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    me = await client.get("/me", headers=headers)
    assert me.status_code == 200
    ws = await client.post(
        "/workspaces", headers=headers, json={"name": "Auth Workspace"}
    )
    assert ws.status_code == 201


@pytest.mark.asyncio
async def test_login_rejects_bad_password(client):
    email = f"badpass-{pytest.__version__}@example.com"
    # unique email
    import uuid

    email = f"{uuid.uuid4()}@example.com"
    signup = await client.post(
        "/auth/signup", json={"email": email, "password": "securepass1-beta"}
    )
    assert signup.status_code == 201
    bad = await client.post(
        "/auth/login", json={"email": email, "password": "wrong-password"}
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_auth_mode_endpoint(client):
    res = await client.get("/auth/mode")
    assert res.status_code == 200
    assert res.json()["auth_mode"] == "local"
