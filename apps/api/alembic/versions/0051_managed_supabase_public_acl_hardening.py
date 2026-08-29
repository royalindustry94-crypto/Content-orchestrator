"""Harden managed-Supabase public schema ACLs and helper functions.

Revision ID: 0051
Revises: 0050

Supabase configures default privileges for its API roles in ``public``. Those
privileges are appropriate for projects that intentionally expose PostgREST
objects, but Content Orchestrator routes application data through the
``app_runtime`` database role and must not expose its tables/RPC helpers
through ``anon`` or ``authenticated``.

This migration is intentionally one-way from a security perspective: the
Alembic downgrade does not restore broad public/API-role privileges.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_API_ROLES: tuple[str, ...] = ("anon", "authenticated")

_APP_FUNCTIONS: tuple[str, ...] = (
    "app_current_user_id()",
    "app_user_has_workspace_role(uuid, workspace_role[])",
    "content_orchestrator_handle_new_auth_user()",
    "is_workspace_admin(uuid, uuid)",
    "is_workspace_creator(uuid, uuid)",
    "is_workspace_member(uuid, uuid)",
    "prevent_delete()",
    "prevent_update()",
    "set_version_and_updated_at()",
)

_RUNTIME_HELPERS: tuple[str, ...] = (
    "app_current_user_id()",
    "app_user_has_workspace_role(uuid, workspace_role[])",
    "is_workspace_admin(uuid, uuid)",
    "is_workspace_creator(uuid, uuid)",
    "is_workspace_member(uuid, uuid)",
)

_MUTABLE_SEARCH_PATH_FUNCTIONS: tuple[str, ...] = (
    "app_current_user_id()",
    "app_user_has_workspace_role(uuid, workspace_role[])",
    "prevent_delete()",
    "prevent_update()",
    "set_version_and_updated_at()",
)


def _revoke_api_role_access(role: str) -> None:
    # Roles such as anon/authenticated exist on managed Supabase but not on the
    # local/CI Postgres bootstrap. Guard each role so the migration remains
    # portable while failing closed whenever the managed role is present.
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN
                EXECUTE 'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM {role}';
                EXECUTE 'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM {role}';
                EXECUTE 'REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA public FROM {role}';

                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL PRIVILEGES ON TABLES FROM {role}';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE ALL PRIVILEGES ON SEQUENCES FROM {role}';
                EXECUTE 'ALTER DEFAULT PRIVILEGES IN SCHEMA public '
                        'REVOKE EXECUTE ON FUNCTIONS FROM {role}';
            END IF;
        END
        $$;
        """
    )


def upgrade() -> None:
    for role in _API_ROLES:
        _revoke_api_role_access(role)

    # PostgreSQL grants EXECUTE on newly-created functions to PUBLIC unless the
    # creator's default privileges say otherwise. Remove that inherited RPC
    # path for both existing and future app functions.
    for signature in _APP_FUNCTIONS:
        op.execute(f"REVOKE EXECUTE ON FUNCTION {signature} FROM PUBLIC;")

    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC;"
    )

    # RLS policy helpers are called by app_runtime and need explicit EXECUTE
    # once PUBLIC execution is removed. Trigger-only helpers stay uncallable by
    # the runtime role unless a future migration explicitly requires it.
    for signature in _RUNTIME_HELPERS:
        op.execute(f"GRANT EXECUTE ON FUNCTION {signature} TO app_runtime;")

    # Pin search_path for the non-SECURITY-DEFINER helpers that Supabase's
    # advisor reports as mutable. SECURITY DEFINER helpers were already pinned
    # by their defining migrations.
    for signature in _MUTABLE_SEARCH_PATH_FUNCTIONS:
        op.execute(f"ALTER FUNCTION {signature} SET search_path = public, pg_temp;")


def downgrade() -> None:
    # Security hardening is intentionally non-reversible. Alembic may move the
    # revision marker back to 0050 for replay testing, but must never restore
    # broad API-role or PUBLIC privileges.
    pass
