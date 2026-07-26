"""Workstream 1 acceptance tests: worker registry, credentials,
heartbeats, capability model, offline detection, RLS.

Runs against real PostgreSQL through the actual roles — the RLS probes
connect as `app_runtime` with `request.jwt.claim.sub` set, exactly as
production requests do.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import select, text

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal, RuntimeSessionLocal
from app.services.workers import compute_liveness, mark_stale_workers_offline

settings = get_settings()

STAGES = ["scripting"]


async def _make_user() -> tuple[str, dict]:
    """A distinct user (id, auth headers) — needed because fixtures are
    cached per test, so requesting `new_user` twice yields the SAME user."""
    from tests.conftest import make_token

    user_id = str(uuid.uuid4())
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO auth.users (id, email) VALUES (:id, :e)"),
            {"id": user_id, "e": f"{user_id}@example.com"},
        )
        await session.commit()
    return user_id, {"Authorization": f"Bearer {make_token(user_id=user_id)}"}


async def _provision(client, headers, workspace_id, name=None, max_concurrency=2):
    response = await client.post(
        f"/workspaces/{workspace_id}/workers",
        headers=headers,
        json={
            "name": name or f"w-{uuid.uuid4().hex[:8]}",
            "supported_stages": STAGES,
            "max_concurrency": max_concurrency,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _worker_headers(provisioned):
    return {"Authorization": f"Bearer {provisioned['worker_secret']}"}


def _register_body(**overrides):
    body = {
        "supported_stages": STAGES,
        "capabilities": {"protocol_version": 1, "providers": [], "features": ["scripting"]},
        "worker_version": "test-1.0",
        "max_concurrency": 2,
    }
    body.update(overrides)
    return body


@pytest_asyncio.fixture
async def workspace_admin(client, new_user):
    """(workspace_id, admin_headers) — a fresh workspace whose creator is admin."""
    user_id, _token, headers = new_user
    response = await client.post("/workspaces", headers=headers, json={"name": "ws1-tests"})
    assert response.status_code == 201, response.text
    return response.json()["id"], headers, user_id


# --------------------------------------------------------------------------
# Provisioning, registration, idempotency
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_and_register(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)

    response = await client.post(
        "/workers/register", headers=_worker_headers(provisioned), json=_register_body()
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["worker_id"] == provisioned["worker_id"]
    assert body["status"] == "online"
    assert body["accepted_protocol_version"] == 1


@pytest.mark.asyncio
async def test_duplicate_registration_is_idempotent(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)

    first = await client.post("/workers/register", headers=wh, json=_register_body())
    second = await client.post(
        "/workers/register", headers=wh, json=_register_body(worker_version="test-1.1")
    )
    assert first.status_code == 200 and second.status_code == 200

    listing = await client.get(f"/workspaces/{workspace_id}/workers", headers=headers)
    rows = [w for w in listing.json() if w["id"] == provisioned["worker_id"]]
    assert len(rows) == 1  # one row, not two
    assert rows[0]["worker_version"] == "test-1.1"  # second registration won


@pytest.mark.asyncio
async def test_concurrent_registration_single_row(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)

    responses = await asyncio.gather(
        *[client.post("/workers/register", headers=wh, json=_register_body()) for _ in range(5)]
    )
    assert all(r.status_code == 200 for r in responses)
    listing = await client.get(f"/workspaces/{workspace_id}/workers", headers=headers)
    assert len([w for w in listing.json() if w["id"] == provisioned["worker_id"]]) == 1


@pytest.mark.asyncio
async def test_unsupported_protocol_version_rejected(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    response = await client.post(
        "/workers/register",
        headers=_worker_headers(provisioned),
        json=_register_body(capabilities={"protocol_version": 99, "providers": [], "features": []}),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_malformed_capabilities_rejected(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    response = await client.post(
        "/workers/register",
        headers=_worker_headers(provisioned),
        json=_register_body(
            capabilities={"protocol_version": 1, "unknown_field": True, "providers": []}
        ),
    )
    assert response.status_code == 422  # extra=forbid: unknown keys fail loudly


# --------------------------------------------------------------------------
# Heartbeats
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_updates_and_appends_history(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())

    response = await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "busy", "current_load": 1}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "busy"
    assert response.json()["liveness"] == "healthy"

    history = await client.get(
        f"/workspaces/{workspace_id}/workers/{provisioned['worker_id']}/heartbeats",
        headers=headers,
    )
    assert history.status_code == 200
    assert len(history.json()) >= 1


@pytest.mark.asyncio
async def test_heartbeat_replay_is_tolerated(client, workspace_admin):
    """Duplicate delivery: the same heartbeat twice (and concurrently) must
    not error or corrupt state — registry converges, history appends."""
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())

    payload = {"status": "online", "current_load": 0}
    responses = await asyncio.gather(
        *[client.post("/workers/heartbeat", headers=wh, json=payload) for _ in range(4)]
    )
    assert all(r.status_code == 200 for r in responses)
    detail = await client.get(
        f"/workspaces/{workspace_id}/workers/{provisioned['worker_id']}", headers=headers
    )
    assert detail.json()["current_load"] == 0
    assert detail.json()["status"] == "online"


@pytest.mark.asyncio
async def test_heartbeat_load_over_capacity_rejected(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id, max_concurrency=2)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body(max_concurrency=2))
    response = await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "busy", "current_load": 3}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_heartbeat_cannot_report_offline(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())
    response = await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "offline", "current_load": 0}
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------
# Deregistration, revocation, expiry, rotation
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deregister_terminal_and_revivable(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())

    first = await client.post("/workers/deregister", headers=wh)
    assert first.status_code == 200
    assert first.json()["status"] == "offline"
    # idempotent repeat
    second = await client.post("/workers/deregister", headers=wh)
    assert second.status_code == 200
    # stale heartbeat against a deregistered worker → 410
    hb = await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "online", "current_load": 0}
    )
    assert hb.status_code == 410
    # re-registration revives the same row
    revive = await client.post("/workers/register", headers=wh, json=_register_body())
    assert revive.status_code == 200
    detail = await client.get(
        f"/workspaces/{workspace_id}/workers/{provisioned['worker_id']}", headers=headers
    )
    assert detail.json()["deregistered_at"] is None
    assert detail.json()["status"] == "online"


@pytest.mark.asyncio
async def test_revoked_worker_rejected(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())

    revoke = await client.post(
        f"/workspaces/{workspace_id}/workers/{provisioned['worker_id']}/credentials/revoke",
        headers=headers,
    )
    assert revoke.status_code == 200
    assert revoke.json()["revoked"] >= 1

    response = await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "online", "current_load": 0}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_credential_rejected(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE worker_credentials SET expires_at = now() - interval '1 second' "
                 "WHERE id = :id"),
            {"id": provisioned["credential_id"]},
        )
        await session.commit()
    response = await client.post(
        "/workers/heartbeat",
        headers=_worker_headers(provisioned),
        json={"status": "online", "current_load": 0},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_secret_rotation_zero_downtime(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    old_headers = _worker_headers(provisioned)
    await client.post("/workers/register", headers=old_headers, json=_register_body())

    rotate = await client.post(
        f"/workspaces/{workspace_id}/workers/{provisioned['worker_id']}/credentials/rotate",
        headers=headers,
    )
    assert rotate.status_code == 200
    rotated = rotate.json()
    new_headers = {"Authorization": f"Bearer {rotated['worker_secret']}"}

    # BOTH credentials work during the grace window (zero downtime)…
    old_ok = await client.post(
        "/workers/heartbeat", headers=old_headers, json={"status": "online", "current_load": 0}
    )
    new_ok = await client.post(
        "/workers/heartbeat", headers=new_headers, json={"status": "online", "current_load": 0}
    )
    assert old_ok.status_code == 200 and new_ok.status_code == 200

    # …and the old one dies once its grace expiry passes.
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("UPDATE worker_credentials SET expires_at = now() - interval '1 second' "
                 "WHERE id = :id"),
            {"id": provisioned["credential_id"]},
        )
        await session.commit()
    old_dead = await client.post(
        "/workers/heartbeat", headers=old_headers, json={"status": "online", "current_load": 0}
    )
    assert old_dead.status_code == 401
    still_new_ok = await client.post(
        "/workers/heartbeat", headers=new_headers, json={"status": "online", "current_load": 0}
    )
    assert still_new_ok.status_code == 200


# --------------------------------------------------------------------------
# Auth failure modes
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_worker_endpoints_reject_bad_auth(client, workspace_admin, new_user):
    _, _, _ = workspace_admin
    _, _, user_headers = new_user
    for headers in (
        None,
        {"Authorization": "Bearer not-even-a-credential"},
        {"Authorization": f"Bearer {uuid.uuid4()}.wrong-secret"},
        user_headers,  # a user JWT is not a worker credential
    ):
        kwargs = {"json": _register_body()}
        if headers is not None:
            kwargs["headers"] = headers
        response = await client.post("/workers/register", **kwargs)
        assert response.status_code == 401, (headers, response.status_code)


@pytest.mark.asyncio
async def test_worker_credential_rejected_on_user_routes(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    response = await client.get(
        f"/workspaces/{workspace_id}/workers", headers=_worker_headers(provisioned)
    )
    assert response.status_code == 401  # worker secret is not a JWT


# --------------------------------------------------------------------------
# Offline detection & liveness (server-driven, clock-controlled)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stale_heartbeat_offline_detection(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())
    worker_id = provisioned["worker_id"]

    async with AsyncSessionLocal() as session:
        # 89s silent: below threshold — sweep must NOT flip it.
        await session.execute(
            text("UPDATE worker_registry SET last_heartbeat_at = now() - interval '89 seconds' "
                 "WHERE id = :id"),
            {"id": worker_id},
        )
        flipped = await mark_stale_workers_offline(session, offline_after_seconds=90)
        await session.commit()
    detail = await client.get(f"/workspaces/{workspace_id}/workers/{worker_id}", headers=headers)
    assert detail.json()["status"] == "online"

    async with AsyncSessionLocal() as session:
        # 91s silent: over threshold — sweep flips it and zeroes load.
        await session.execute(
            text("UPDATE worker_registry SET last_heartbeat_at = now() - interval '91 seconds' "
                 "WHERE id = :id"),
            {"id": worker_id},
        )
        await mark_stale_workers_offline(session, offline_after_seconds=90)
        # idempotent second run
        again = await mark_stale_workers_offline(session, offline_after_seconds=90)
        await session.commit()
    detail = await client.get(f"/workspaces/{workspace_id}/workers/{worker_id}", headers=headers)
    assert detail.json()["status"] == "offline"
    assert detail.json()["current_load"] == 0
    assert detail.json()["liveness"] == "dead"
    del flipped, again  # counts vary with other tests' workers; state asserted above


@pytest.mark.asyncio
async def test_rotate_revoke_serialized_kill_switch(client, workspace_admin):
    """Adversarial: a revoke (kill switch) concurrent with an in-flight
    rotate must not leave a live credential. We simulate rotate holding
    the worker row lock with a freshly-inserted (uncommitted) ACTIVE
    credential; revoke must BLOCK on that lock, and once rotate commits,
    revoke must see and kill the new credential too — final ACTIVE = 0.

    Without worker-row locking in both paths, revoke's SELECT would run
    before the new credential is committed, revoke only the old one, and
    strand the new credential ACTIVE after a "kill".
    """
    from app.core.worker_auth import generate_worker_secret, hash_worker_secret
    from app.models.enums import WorkerCredentialStatus
    from app.models.workers import WorkerCredential, WorkerRegistration

    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    worker_id = uuid.UUID(provisioned["worker_id"])

    hold = AsyncSessionLocal()
    await hold.__aenter__()
    try:
        # rotate-in-flight: lock the worker row, insert a new ACTIVE cred, no commit yet.
        await hold.get(WorkerRegistration, worker_id, with_for_update=True)
        hold.add(
            WorkerCredential(
                worker_id=worker_id,
                workspace_id=uuid.UUID(workspace_id),
                secret_hash=hash_worker_secret(generate_worker_secret()),
            )
        )
        await hold.flush()

        revoke_task = asyncio.create_task(
            client.post(
                f"/workspaces/{workspace_id}/workers/{worker_id}/credentials/revoke",
                headers=headers,
            )
        )
        await asyncio.sleep(0.5)
        assert not revoke_task.done(), "revoke did not serialize behind the worker row lock"

        await hold.commit()  # rotate commits its new credential
    finally:
        await hold.__aexit__(None, None, None)

    response = await revoke_task
    assert response.status_code == 200
    assert response.json()["revoked"] >= 2  # old + the concurrently-created one

    async with AsyncSessionLocal() as session:
        active = (
            await session.execute(
                select(WorkerCredential).where(
                    WorkerCredential.worker_id == worker_id,
                    WorkerCredential.status == WorkerCredentialStatus.ACTIVE,
                )
            )
        ).scalars().all()
    assert active == []  # kill switch left nothing alive


def test_liveness_thresholds():
    now = datetime.now(UTC)
    kw = {"now": now, "suspect_after_seconds": 30, "offline_after_seconds": 90}
    assert compute_liveness(now - timedelta(seconds=29), **kw) == "healthy"
    assert compute_liveness(now - timedelta(seconds=31), **kw) == "suspect"
    assert compute_liveness(now - timedelta(seconds=91), **kw) == "dead"
    assert compute_liveness(None, **kw) == "dead"


# --------------------------------------------------------------------------
# Drain
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drain_admin_only_and_preserved_across_register(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())
    worker_id = provisioned["worker_id"]

    drain = await client.post(
        f"/workspaces/{workspace_id}/workers/{worker_id}/drain",
        headers=headers, json={"drain": True},
    )
    assert drain.status_code == 200 and drain.json()["drain"] is True

    # re-registration must NOT clear admin drain intent
    await client.post("/workers/register", headers=wh, json=_register_body())
    detail = await client.get(f"/workspaces/{workspace_id}/workers/{worker_id}", headers=headers)
    assert detail.json()["drain"] is True

    # non-member cannot drain
    _, outsider_headers = await _make_user()
    forbidden = await client.post(
        f"/workspaces/{workspace_id}/workers/{worker_id}/drain",
        headers=outsider_headers, json={"drain": False},
    )
    assert forbidden.status_code == 403


# --------------------------------------------------------------------------
# Cross-workspace + RLS adversarial probes
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cross_workspace_worker_invisible(client, workspace_admin):
    workspace_id, headers, _ = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    worker_id = provisioned["worker_id"]

    outsider_id, outsider_headers = await _make_user()
    # HTTP: outsider is not a member → guard rejects listing/detail/heartbeats
    for path in (
        f"/workspaces/{workspace_id}/workers",
        f"/workspaces/{workspace_id}/workers/{worker_id}",
        f"/workspaces/{workspace_id}/workers/{worker_id}/heartbeats",
    ):
        response = await client.get(path, headers=outsider_headers)
        assert response.status_code == 403, path

    # SQL as app_runtime: RLS hides the pinned worker row entirely.
    async with RuntimeSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('request.jwt.claim.sub', :sub, true)"),
            {"sub": outsider_id},
        )
        count = (
            await session.execute(
                text("SELECT count(*) FROM worker_registry WHERE id = :id"),
                {"id": worker_id},
            )
        ).scalar()
        assert count == 0


@pytest.mark.asyncio
async def test_rls_heartbeats_admin_only_and_registry_readonly(client, workspace_admin):
    workspace_id, admin_headers, admin_id = workspace_admin
    provisioned = await _provision(client, headers=admin_headers, workspace_id=workspace_id)
    wh = _worker_headers(provisioned)
    await client.post("/workers/register", headers=wh, json=_register_body())
    await client.post(
        "/workers/heartbeat", headers=wh, json={"status": "online", "current_load": 0}
    )
    worker_id = provisioned["worker_id"]

    # Add a normal (non-admin) member to the workspace.
    member_id, _member_headers = await _make_user()
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("INSERT INTO workspace_memberships (workspace_id, user_id, role) "
                 "VALUES (:ws, :u, 'reviewer')"),
            {"ws": workspace_id, "u": member_id},
        )
        await session.commit()

    async def _as(sub: str, sql: str, params: dict):
        async with RuntimeSessionLocal() as session:
            await session.execute(
                text("SELECT set_config('request.jwt.claim.sub', :sub, true)"), {"sub": sub}
            )
            return await session.execute(text(sql), params)

    # Admin sees heartbeat telemetry (amendment 2)…
    admin_count = (
        await _as(admin_id, "SELECT count(*) FROM worker_heartbeats WHERE worker_id = :w",
                  {"w": worker_id})
    ).scalar()
    assert admin_count >= 1
    # …a normal member does not…
    member_count = (
        await _as(member_id, "SELECT count(*) FROM worker_heartbeats WHERE worker_id = :w",
                  {"w": worker_id})
    ).scalar()
    assert member_count == 0
    # …but the member DOES see the registry row itself (workers_select).
    registry_count = (
        await _as(member_id, "SELECT count(*) FROM worker_registry WHERE id = :w",
                  {"w": worker_id})
    ).scalar()
    assert registry_count == 1

    # User roles can never write the registry (no write policies → under
    # FORCE RLS the UPDATE's row visibility is empty: 0 rows touched).
    result = await _as(
        admin_id,
        "UPDATE worker_registry SET name = 'hacked' WHERE id = :w",
        {"w": worker_id},
    )
    assert result.rowcount == 0
    name_after = (
        await _as(admin_id, "SELECT name FROM worker_registry WHERE id = :w", {"w": worker_id})
    ).scalar()
    assert name_after != "hacked"
    # …and worker_credentials is completely invisible (no grants/policies).
    with pytest.raises(Exception, match="permission denied|insufficient_privilege"):
        await _as(admin_id, "SELECT count(*) FROM worker_credentials", {})


@pytest.mark.asyncio
async def test_rls_registry_update_returns_zero_rows_or_errors(client, workspace_admin):
    """UPDATE without RETURNING as app_runtime: under FORCE RLS with no
    UPDATE policy the statement affects 0 rows (or errors) — either way
    the row is untouched."""
    workspace_id, headers, admin_id = workspace_admin
    provisioned = await _provision(client, headers, workspace_id)
    worker_id = provisioned["worker_id"]
    try:
        async with RuntimeSessionLocal() as session:
            await session.execute(
                text("SELECT set_config('request.jwt.claim.sub', :sub, true)"), {"sub": admin_id}
            )
            result = await session.execute(
                text("UPDATE worker_registry SET current_load = 0 WHERE id = :w"),
                {"w": worker_id},
            )
            assert result.rowcount == 0
            await session.rollback()
    except Exception:
        pass  # an outright RLS error is equally acceptable — write denied
    detail = await client.get(f"/workspaces/{workspace_id}/workers/{worker_id}", headers=headers)
    assert detail.status_code == 200  # row intact and still visible to admin
