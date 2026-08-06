"""P0: local email/password auth minting Supabase-shaped JWTs."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_signup_login_and_create_workspace(client):
    email = "beta.user@example.com"
    password = "securepass1"
    signup = await client.post(
        "/auth/signup",
        json={"email": email, "password": password, "full_name": "Beta User"},
    )
    # email may already exist from prior run — accept 201 or login path
    if signup.status_code == 409:
        login = await client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
    else:
        assert signup.status_code == 201, signup.text
        token = signup.json()["access_token"]
        assert signup.json()["email"] == email

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
        "/auth/signup", json={"email": email, "password": "securepass1"}
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
