"""Milestone 2: Identity and Access Foundation

Revision ID: 0001
Revises:
Create Date: 2026-07-21

Creates profiles/workspaces/workspace_memberships, the app_runtime role
used for RLS-enforced request traffic, and the RLS policies themselves.
See docs/milestone-2-identity-and-access.md for the design rationale.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    # --- auth.users shim for local dev / CI parity -------------------
    # On real Supabase, `auth` and `auth.users` already exist with the
    # platform's own columns — these are no-ops there. In plain Postgres
    # (Docker/CI), this creates just enough surface for the profile
    # trigger and FK integrity to be testable end-to-end.
    op.execute("CREATE SCHEMA IF NOT EXISTS auth;")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.users (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            email text
        );
        """
    )

    # --- app_runtime role ---------------------------------------------
    # Non-owner role that request traffic connects as (APP_DATABASE_URL),
    # so RLS policies actually apply instead of being bypassed by table
    # ownership. Deploying against real Supabase: create this role (or an
    # equivalent) once via the SQL editor if the migration role lacks
    # CREATE ROLE privilege there — the GRANTs below are what matter and
    # are safe to re-run.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_runtime') THEN
                CREATE ROLE app_runtime LOGIN PASSWORD 'app_runtime' NOBYPASSRLS NOCREATEROLE NOCREATEDB;
            END IF;
        END
        $$;
        """
    )

    # --- workspace_role enum -------------------------------------------
    workspace_role = sa.Enum("admin", "editor", "reviewer", name="workspace_role")
    workspace_role.create(op.get_bind(), checkfirst=True)

    # --- profiles --------------------------------------------------------
    op.create_table(
        "profiles",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # --- workspaces ------------------------------------------------------
    op.create_table(
        "workspaces",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("created_by", PG_UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # --- workspace_memberships -------------------------------------------
    op.create_table(
        "workspace_memberships",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("workspace_id", PG_UUID(as_uuid=True), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", PG_UUID(as_uuid=True), sa.ForeignKey("profiles.id", ondelete="CASCADE"), nullable=False),
        # Reference the type created above WITHOUT re-emitting CREATE TYPE.
        # Passing the sa.Enum object itself makes create_table issue a second
        # CREATE TYPE (no checkfirst) -> DuplicateObjectError on fresh DBs.
        sa.Column("role", PG_ENUM(name="workspace_role", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    # --- grants for app_runtime ------------------------------------------
    # One statement per op.execute: asyncpg uses prepared statements, which
    # reject multiple commands in a single call.
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON profiles, workspaces, workspace_memberships TO app_runtime;"
    )
    op.execute("GRANT USAGE ON SCHEMA public TO app_runtime;")

    # --- app_current_user_id() -------------------------------------------
    # Reads a GUC that FastAPI sets per-transaction after verifying the
    # Supabase JWT (see app/db/session.py: rls_scoped_session). Not
    # Supabase's auth.uid() — see docs/milestone-2-identity-and-access.md §1
    # for why this app defines its own.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid AS $$
          SELECT NULLIF(current_setting('request.jwt.claim.sub', true), '')::uuid
        $$ LANGUAGE sql STABLE;
        """
    )

    # --- RLS: profiles -----------------------------------------------------
    op.execute("ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE profiles FORCE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY profiles_select_authenticated ON profiles "
        "FOR SELECT USING (app_current_user_id() IS NOT NULL);"
    )
    op.execute(
        "CREATE POLICY profiles_insert_own ON profiles "
        "FOR INSERT WITH CHECK (id = app_current_user_id());"
    )
    op.execute(
        "CREATE POLICY profiles_update_own ON profiles "
        "FOR UPDATE USING (id = app_current_user_id());"
    )

    # --- RLS: workspaces -----------------------------------------------------
    op.execute("ALTER TABLE workspaces ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workspaces FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY workspaces_select_member ON workspaces
            FOR SELECT USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspaces.id
                          AND m.user_id = app_current_user_id())
            );
        """
    )
    op.execute(
        "CREATE POLICY workspaces_insert_any_authenticated ON workspaces "
        "FOR INSERT WITH CHECK (created_by = app_current_user_id());"
    )
    op.execute(
        """
        CREATE POLICY workspaces_update_admin ON workspaces
            FOR UPDATE USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspaces.id
                          AND m.user_id = app_current_user_id()
                          AND m.role = 'admin')
            );
        """
    )

    # --- RLS: workspace_memberships -------------------------------------------
    op.execute("ALTER TABLE workspace_memberships ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workspace_memberships FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY memberships_select_same_workspace ON workspace_memberships
            FOR SELECT USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspace_memberships.workspace_id
                          AND m.user_id = app_current_user_id())
            );
        """
    )
    op.execute(
        """
        CREATE POLICY memberships_write_admin_only ON workspace_memberships
            FOR ALL USING (
                EXISTS (SELECT 1 FROM workspace_memberships m
                        WHERE m.workspace_id = workspace_memberships.workspace_id
                          AND m.user_id = app_current_user_id()
                          AND m.role = 'admin')
            );
        """
    )

    # --- profile-on-signup trigger -----------------------------------------
    # No-op-safe on real Supabase in the sense that it only ever inserts
    # into `profiles`, which this migration owns; it does not touch
    # Supabase's own auth schema beyond attaching a trigger to auth.users.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION handle_new_auth_user() RETURNS trigger AS $$
        BEGIN
            INSERT INTO profiles (id, email)
            VALUES (NEW.id, COALESCE(NEW.email, ''))
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute(
        """
        CREATE TRIGGER on_auth_user_created
            AFTER INSERT ON auth.users
            FOR EACH ROW EXECUTE FUNCTION handle_new_auth_user();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;")
    op.execute("DROP FUNCTION IF EXISTS handle_new_auth_user();")

    op.execute("DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_select_same_workspace ON workspace_memberships;")
    op.execute("DROP POLICY IF EXISTS workspaces_update_admin ON workspaces;")
    op.execute("DROP POLICY IF EXISTS workspaces_insert_any_authenticated ON workspaces;")
    op.execute("DROP POLICY IF EXISTS workspaces_select_member ON workspaces;")
    op.execute("DROP POLICY IF EXISTS profiles_update_own ON profiles;")
    op.execute("DROP POLICY IF EXISTS profiles_insert_own ON profiles;")
    op.execute("DROP POLICY IF EXISTS profiles_select_authenticated ON profiles;")

    op.execute("DROP FUNCTION IF EXISTS app_current_user_id();")

    op.drop_table("workspace_memberships")
    op.drop_table("workspaces")
    op.drop_table("profiles")

    sa.Enum(name="workspace_role").drop(op.get_bind(), checkfirst=True)

    op.execute("REVOKE ALL ON SCHEMA public FROM app_runtime;")
    # app_runtime role itself is left in place intentionally — dropping a
    # role that other objects/grants may still reference is a manual,
    # reviewed operation, not an automatic part of a schema downgrade.
