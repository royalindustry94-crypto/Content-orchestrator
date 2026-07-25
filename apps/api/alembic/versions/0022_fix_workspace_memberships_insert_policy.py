"""Fix workspace_memberships INSERT policy to unblock workspace creation.

The original ``memberships_write_admin_only FOR ALL`` policy used its USING
expression as the implicit WITH CHECK for INSERTs. Since the USING expression
requires the current user to already be an admin in the workspace, inserting
the very first membership (creator seeding their own admin row) was always
rejected — a chicken-and-egg deadlock.

This migration:
1. Drops the overly broad FOR ALL policy.
2. Adds a targeted FOR INSERT policy that allows:
   a. Any existing workspace admin to add a member.
   b. The workspace creator to insert their own first admin membership when
      no memberships exist yet.
3. Adds separate FOR UPDATE and FOR DELETE policies requiring admin status.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_write_admin_only ON workspace_memberships;")

    # INSERT: admin promoting someone else, OR creator seeding their first
    # admin membership in a workspace that has no members yet.
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
                        WHERE id = workspace_id
                          AND created_by = app_current_user_id()
                    )
                    AND NOT EXISTS (
                        SELECT 1 FROM workspace_memberships existing
                        WHERE existing.workspace_id = workspace_memberships.workspace_id
                    )
                )
            );
        """
    )

    # UPDATE and DELETE: admins only.
    op.execute(
        """
        CREATE POLICY memberships_update ON workspace_memberships
            FOR UPDATE
            USING (is_workspace_admin(workspace_id, app_current_user_id()));
        """
    )
    op.execute(
        """
        CREATE POLICY memberships_delete ON workspace_memberships
            FOR DELETE
            USING (is_workspace_admin(workspace_id, app_current_user_id()));
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_delete ON workspace_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_update ON workspace_memberships;")
    op.execute("DROP POLICY IF EXISTS memberships_insert ON workspace_memberships;")

    op.execute(
        """
        CREATE POLICY memberships_write_admin_only ON workspace_memberships
            FOR ALL USING (
                is_workspace_admin(workspace_id, app_current_user_id())
            );
        """
    )
