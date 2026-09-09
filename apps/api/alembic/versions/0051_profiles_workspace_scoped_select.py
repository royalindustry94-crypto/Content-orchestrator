"""Fix: scope `profiles` SELECT to shared-workspace members, not any authenticated user.

Revision ID: 0051
Revises: 0050
Create Date: 2026-09-07

Independent audit finding (2026-09-07, Claude cross-check of issue #91
Section 1/3): `profiles_select_authenticated` (migration 0001) only checked
`app_current_user_id() IS NOT NULL` — any authenticated user, from any
workspace, could read every other user's email/full_name through the
`app_runtime` role. `FORCE ROW LEVEL SECURITY` was enabled (the mechanism
was present) but the policy itself provided no tenant isolation, which is
this project's own documented non-negotiable ("workspace isolation via
FORCE RLS", AGENTS.md).

Replaces that policy with one scoped to: the caller's own profile, or a
profile belonging to a user who shares at least one workspace with the
caller (the actual product need — e.g. listing a workspace's members).
No route currently reads `profiles` beyond `GET /me` (own row only), so
this closes a defense-in-depth gap rather than an active exploit.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS profiles_select_authenticated ON profiles;")
    op.execute(
        """
        CREATE POLICY profiles_select_self_or_shared_workspace ON profiles
            FOR SELECT USING (
                id = app_current_user_id()
                OR EXISTS (
                    SELECT 1
                    FROM workspace_memberships caller_m
                    JOIN workspace_memberships target_m
                      ON target_m.workspace_id = caller_m.workspace_id
                    WHERE caller_m.user_id = app_current_user_id()
                      AND target_m.user_id = profiles.id
                )
            );
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS profiles_select_self_or_shared_workspace ON profiles;"
    )
    op.execute(
        "CREATE POLICY profiles_select_authenticated ON profiles "
        "FOR SELECT USING (app_current_user_id() IS NOT NULL);"
    )
