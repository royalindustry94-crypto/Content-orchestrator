"""Fix memberships_delete RLS policy to allow members to leave their own workspace.

The memberships_delete policy added in 0022 only allowed workspace admins to
delete memberships. This blocked non-admin members from removing themselves
(self-leave), even though the application layer (remove_member route) correctly
gates the action. The ORM DELETE executed by the route was silently suppressed
by RLS (DELETE 0 rows), while the route returned 204 — a silent data-integrity
defect where the membership row survived the leave action.

Fix: expand the USING clause to also allow user_id = app_current_user_id()
(the member deleting their own row).

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-25
"""

from alembic import op

revision: str = "0024"
down_revision: str = "0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_delete ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_delete ON workspace_memberships
            FOR DELETE
            USING (
                is_workspace_admin(workspace_id, app_current_user_id())
                OR user_id = app_current_user_id()
            );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS memberships_delete ON workspace_memberships;")
    op.execute(
        """
        CREATE POLICY memberships_delete ON workspace_memberships
            FOR DELETE
            USING (is_workspace_admin(workspace_id, app_current_user_id()));
        """
    )
