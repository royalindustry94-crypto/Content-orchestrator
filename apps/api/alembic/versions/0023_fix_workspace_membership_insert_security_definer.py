"""Add is_workspace_creator() and fix memberships_insert policy.

The memberships_insert policy added in 0022 used a plain
``EXISTS (SELECT 1 FROM workspaces WHERE id = workspace_id AND created_by = ...)``
subquery to verify the inserting user is the workspace owner. Because the
``workspaces`` table has FORCE ROW LEVEL SECURITY and the workspaces_select_member
policy hides the workspace row from a user who is not yet a member, that EXISTS
always returns FALSE, so the creator can never insert the first membership row.

Fix: add ``is_workspace_creator(wsid uuid, uid uuid)`` as a SECURITY DEFINER
function (runs as the table-owning superuser, bypassing RLS) and update the
memberships_insert policy to use it.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION is_workspace_creator(wsid uuid, uid uuid)
        RETURNS boolean
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public
        AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspaces
                WHERE id = wsid AND created_by = uid
            );
        $$;
        """
    )

    # Recreate memberships_insert using the new helper.
    op.execute("DROP POLICY IF EXISTS memberships_insert ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_insert ON workspace_memberships
            FOR INSERT
            WITH CHECK (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR (
                    user_id = app_current_user_id()
                    AND role = 'admin'
                    AND is_workspace_creator(workspace_id, app_current_user_id())
                    AND NOT EXISTS (
                        SELECT 1 FROM workspace_memberships existing
                        WHERE existing.workspace_id = workspace_memberships.workspace_id
                    )
                )
            );
        """
    )


def downgrade() -> None:
    # Restore the policy without the is_workspace_creator helper.
    op.execute("DROP POLICY IF EXISTS memberships_insert ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_insert ON workspace_memberships
            FOR INSERT
            WITH CHECK (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR (
                    user_id = app_current_user_id()
                    AND role = 'admin'
                    AND EXISTS (
                        SELECT 1 FROM workspaces
                        WHERE id = workspace_id AND created_by = app_current_user_id()
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM workspace_memberships existing
                        WHERE existing.workspace_id = workspace_memberships.workspace_id
                    )
                )
            );
        """
    )
    op.execute("DROP FUNCTION IF EXISTS is_workspace_creator(uuid, uuid);")
