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
MIGRATION_0051 = API_ROOT / "alembic/versions/0051_managed_supabase_public_acl_hardening.py"
LOCAL_BOOTSTRAP = REPO_ROOT / "scripts/bootstrap_local_postgres.sql"


def _run_psql(psql: str, url: str, sql: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [psql, url, "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
    )


def _database_urls(database_url: str, db_name: str) -> tuple[str, str]:
    parsed = urlsplit(database_url)
    admin_url = urlunsplit(
        (parsed.scheme, parsed.netloc, "/postgres", parsed.query, parsed.fragment)
    )
    target_url = urlunsplit(
        (parsed.scheme, parsed.netloc, f"/{db_name}", parsed.query, parsed.fragment)
    )
    return admin_url, target_url


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


def test_managed_acl_hardening_is_forward_only_and_explicit() -> None:
    source = MIGRATION_0051.read_text()
    assert 'revision: str = "0051"' in source
    assert 'down_revision: str | None = "0050"' in source
    assert "REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC" in source
    assert "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC" in source
    assert "GRANT EXECUTE ON FUNCTION {signature} TO app_runtime" in source
    assert "ALTER FUNCTION {signature} SET search_path = public, pg_temp" in source
    assert "Security hardening is intentionally non-reversible" in source


def test_alembic_behaviorally_fails_without_auth_users() -> None:
    """Prove the managed-auth precondition actually fails closed, not just textually."""
    psql = shutil.which("psql")
    database_url = os.getenv("DATABASE_URL")
    if psql is None or not database_url:
        pytest.skip("behavioral migration guard requires psql and DATABASE_URL")

    db_name = f"missing_auth_guard_{uuid4().hex[:12]}"
    admin_url, guarded_url = _database_urls(database_url, db_name)

    _run_psql(psql, admin_url, f'CREATE DATABASE "{db_name}"')
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
        _run_psql(psql, admin_url, f'DROP DATABASE IF EXISTS "{db_name}"')


def test_managed_supabase_default_acls_are_behaviorally_contained() -> None:
    """Reproduce Supabase API-role defaults and prove 0051 removes the exposure."""
    psql = shutil.which("psql")
    database_url = os.getenv("DATABASE_URL")
    if psql is None or not database_url:
        pytest.skip("managed ACL parity guard requires psql and DATABASE_URL")

    db_name = f"managed_acl_guard_{uuid4().hex[:12]}"
    admin_url, target_url = _database_urls(database_url, db_name)
    created_roles: list[str] = []

    for role in ("anon", "authenticated"):
        exists = _run_psql(
            psql,
            admin_url,
            f"SELECT 1 FROM pg_roles WHERE rolname = '{role}'",
        ).stdout.strip()
        if not exists:
            _run_psql(psql, admin_url, f"CREATE ROLE {role} NOLOGIN")
            created_roles.append(role)

    _run_psql(psql, admin_url, f'CREATE DATABASE "{db_name}"')
    try:
        subprocess.run(
            [psql, target_url, "-v", "ON_ERROR_STOP=1", "-f", str(LOCAL_BOOTSTRAP)],
            check=True,
            capture_output=True,
            text=True,
        )

        # Reproduce the relevant Supabase defaults for objects subsequently
        # created by the migration identity in the public schema.
        _run_psql(
            psql,
            target_url,
            """
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT ALL PRIVILEGES ON TABLES TO anon, authenticated;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT ALL PRIVILEGES ON SEQUENCES TO anon, authenticated;
            ALTER DEFAULT PRIVILEGES IN SCHEMA public
                GRANT EXECUTE ON FUNCTIONS TO anon, authenticated;
            """,
        )

        env = os.environ.copy()
        env["DATABASE_URL"] = target_url
        subprocess.run(
            ["alembic", "upgrade", "head"],
            cwd=API_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

        current_exposure = _run_psql(
            psql,
            target_url,
            """
            SELECT count(*)
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind = 'r'
              AND (
                has_table_privilege('anon', c.oid, 'SELECT,INSERT,UPDATE,DELETE')
                OR has_table_privilege('authenticated', c.oid, 'SELECT,INSERT,UPDATE,DELETE')
              );
            """,
        ).stdout.strip()
        assert current_exposure == "0"

        function_exposure = _run_psql(
            psql,
            target_url,
            """
            SELECT count(*)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.proname IN (
                'app_current_user_id',
                'app_user_has_workspace_role',
                'content_orchestrator_handle_new_auth_user',
                'is_workspace_admin',
                'is_workspace_creator',
                'is_workspace_member',
                'prevent_delete',
                'prevent_update',
                'set_version_and_updated_at'
              )
              AND (
                has_function_privilege('anon', p.oid, 'EXECUTE')
                OR has_function_privilege('authenticated', p.oid, 'EXECUTE')
              );
            """,
        ).stdout.strip()
        assert function_exposure == "0"

        runtime_helpers = _run_psql(
            psql,
            target_url,
            """
            SELECT count(*)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.proname IN (
                'app_current_user_id',
                'app_user_has_workspace_role',
                'is_workspace_admin',
                'is_workspace_creator',
                'is_workspace_member'
              )
              AND has_function_privilege('app_runtime', p.oid, 'EXECUTE');
            """,
        ).stdout.strip()
        assert runtime_helpers == "5"

        pinned_paths = _run_psql(
            psql,
            target_url,
            """
            SELECT count(*)
            FROM pg_proc p
            JOIN pg_namespace n ON n.oid = p.pronamespace
            WHERE n.nspname = 'public'
              AND p.proname IN (
                'app_current_user_id',
                'app_user_has_workspace_role',
                'prevent_delete',
                'prevent_update',
                'set_version_and_updated_at'
              )
              AND 'search_path=public, pg_temp' = ANY(COALESCE(p.proconfig, ARRAY[]::text[]));
            """,
        ).stdout.strip()
        assert pinned_paths == "5"

        # Verify the hardened default ACLs protect objects created *after* 0051.
        _run_psql(
            psql,
            target_url,
            """
            CREATE TABLE public.managed_acl_probe (id integer);
            CREATE SEQUENCE public.managed_acl_probe_seq;
            CREATE FUNCTION public.managed_acl_probe_fn() RETURNS integer
                LANGUAGE sql AS $$ SELECT 1 $$;
            """,
        )
        future_exposure = _run_psql(
            psql,
            target_url,
            """
            SELECT
              has_table_privilege('anon', 'public.managed_acl_probe', 'SELECT')::int || ',' ||
              has_table_privilege('authenticated', 'public.managed_acl_probe', 'SELECT')::int || ',' ||
              has_sequence_privilege('anon', 'public.managed_acl_probe_seq', 'USAGE')::int || ',' ||
              has_sequence_privilege('authenticated', 'public.managed_acl_probe_seq', 'USAGE')::int || ',' ||
              has_function_privilege('anon', 'public.managed_acl_probe_fn()', 'EXECUTE')::int || ',' ||
              has_function_privilege('authenticated', 'public.managed_acl_probe_fn()', 'EXECUTE')::int;
            """,
        ).stdout.strip()
        assert future_exposure == "0,0,0,0,0,0"
    finally:
        _run_psql(psql, admin_url, f'DROP DATABASE IF EXISTS "{db_name}"')
        for role in reversed(created_roles):
            _run_psql(psql, admin_url, f"DROP ROLE IF EXISTS {role}")
