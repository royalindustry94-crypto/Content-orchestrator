"""Regression guards for managed-Supabase migration safety."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
MIGRATION_0001 = REPO_ROOT / "apps/api/alembic/versions/0001_identity_and_access.py"
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


def test_local_bootstrap_is_explicitly_local_only() -> None:
    source = LOCAL_BOOTSTRAP.read_text()
    assert "LOCAL / CI ONLY" in source
    assert "Never apply this file to a managed Supabase project" in source
    assert "CREATE TABLE IF NOT EXISTS auth.users" in source
    assert "PASSWORD 'app_runtime'" in source
