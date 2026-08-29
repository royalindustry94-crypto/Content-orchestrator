"""Regression guards for managed-Supabase migration safety."""

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
API_ROOT = REPO_ROOT / "apps/api"
MIGRATION_0001 = API_ROOT / "alembic/versions/0001_identity_and_access.py"
LOCAL_BOOTSTRAP = REPO_ROOT / "scripts/bootstrap_local_postgres.sql"


def test_canonical_migration_does_not_create_supabase_auth_objects() -> None:
    source = MIGRATION_0001.read_text()
    assert "CREATE SCHEMA IF NOT EXISTS auth" not in source
    assert "CREATE TABLE IF NOT EXISTS auth.users" not in source
    assert "PASSWORD 'app_runtime'" not in source


def test_canonical_migration_fails_closed_without_auth_users() -> None:
    source = MIGRATION_0001.read_text()
    assert "to_regclass('auth.users') IS NULL" in source
    assert "RAISE EXCEPTION" in source


def test_signup_trigger_is_namespaced_and_security_definer_is_hardened() -> None:
    source = MIGRATION_0001.read_text()
    assert "content_orchestrator_on_auth_user_created" in source
    assert "public.content_orchestrator_handle_new_auth_user" in source
    assert "SECURITY DEFINER SET search_path = public, pg_temp" in source


def test_local_bootstrap_is_explicitly_local_only_and_self_refuses_managed() -> None:
    source = LOCAL_BOOTSTRAP.read_text()
    assert "LOCAL / CI ONLY" in source
    assert "Never apply this file" in source
    assert "managed Supabase project" in source
    assert "supabase_auth_admin" in source
    assert "Refusing local bootstrap on managed Supabase" in source
    assert "CREATE TABLE IF NOT EXISTS auth.users" in source
    assert "PASSWORD 'app_runtime'" in source


def test_alembic_behaviorally_fails_without_auth_users() -> None:
    """Prove the managed-auth precondition actually fails closed, not just textually."""
    psql = shutil.which("psql")
    database_url = os.getenv("DATABASE_URL")
    if psql is None or not database_url:
        pytest.skip("behavioral migration guard requires psql and DATABASE_URL")

    parsed = urlsplit(database_url)
    admin_url = urlunsplit(
        (parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment)
    )
    db_name = f"missing_auth_guard_{uuid4().hex[:12]}"
    guarded_url = urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{db_name}", parsed.query, parsed.fragment)
    )

    subprocess.run(
        [psql, admin_url, "-v", "ON_ERROR_STOP=1", "-c", f'CREATE DATABASE "{db_name}"'],
        check=True,
        capture_output=True,
        text=True,
    )
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = guarded_url
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=API_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        output = f"{result.stdout}\n{result.stderr}"
        assert result.returncode != 0
        assert "auth.users is required" in output
    finally:
        drop_database = [
            psql,
            admin_url,
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f'DROP DATABASE IF EXISTS "{db_name}"',
        ]
        subprocess.run(
            drop_database,
            check=True,
            capture_output=True,
            text=True,
        )
