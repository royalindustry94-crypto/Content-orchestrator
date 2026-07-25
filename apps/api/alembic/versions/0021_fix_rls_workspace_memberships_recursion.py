"""Fix: workspace_memberships RLS self-reference causes infinite recursion

PostgreSQL evaluates RLS policies on every row of every query that touches the
protected table. The original `memberships_select_same_workspace` and
`memberships_write_admin_only` policies queried `workspace_memberships` from
within their own USING clauses, triggering the same policies recursively until
PostgreSQL raised InvalidObjectDefinitionError: infinite recursion detected.

Fix: two SECURITY DEFINER helper functions that run as the table owner (who
has BYPASSRLS) break the cycle.

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Helper that checks whether `uid` is any member of workspace `wsid`.
    # SECURITY DEFINER + SET search_path means it runs as the defining role
    # (table owner) which bypasses RLS — breaking the self-reference cycle.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION is_workspace_member(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships
                WHERE workspace_id = wsid AND user_id = uid
            );
        $$;
        """
    )

    # Helper that checks whether `uid` is an admin of workspace `wsid`.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION is_workspace_admin(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships
                WHERE workspace_id = wsid
                  AND user_id = uid
                  AND role = 'admin'
            );
        $$;
        """
    )

    # Recreate both workspace_memberships policies using the helper functions.
    op.execute("DROP POLICY IF EXISTS memberships_select_same_workspace ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_select_same_workspace ON workspace_memberships
            FOR SELECT USING (
                is_workspace_member(workspace_id, app_current_user_id())
            );
        """
    )

    op.execute("DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_write_admin_only ON workspace_memberships
            FOR ALL USING (
                is_workspace_admin(workspace_id, app_current_user_id())
            );
        """
    )

    # The workspaces policies also reference workspace_memberships (from a
    # different table's policy — no recursion there), but update them to use
    # the helpers for consistency and correctness.
    op.execute("DROP POLICY IF EXISTS workspaces_select_member ON workspaces;")
    op.execute(
        """
        CREATE POLICY workspaces_select_member ON workspaces
            FOR SELECT USING (
                is_workspace_member(id, app_current_user_id())
            );
        """
    )

    op.execute("DROP POLICY IF EXISTS workspaces_update_admin ON workspaces;")
    op.execute(
        """
        CREATE POLICY workspaces_update_admin ON workspaces
            FOR UPDATE USING (
                is_workspace_admin(id, app_current_user_id())
            );
        """
    )


def downgrade() -> None:
    # Restore the original (recursive) policies and drop the helpers.
    op.execute("DROP POLICY IF EXISTS memberships_select_same_workspace ON workspace_memberships;")
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
    op.execute("DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;")
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

    op.execute("DROP POLICY IF EXISTS workspaces_select_member ON workspaces;")
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
    op.execute("DROP POLICY IF EXISTS workspaces_update_admin ON workspaces;")
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

    op.execute("DROP FUNCTION IF EXISTS is_workspace_admin(uuid, uuid);")
    op.execute("DROP FUNCTION IF EXISTS is_workspace_member(uuid, uuid);")
