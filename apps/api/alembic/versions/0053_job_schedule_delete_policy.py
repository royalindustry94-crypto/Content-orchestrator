"""Add the missing job_schedule DELETE RLS policy.

Revision ID: 0053
Revises: 0052
Create Date: 2026-09-08

TD-083 (2026-09-08 data-governance audit): `job_schedule` is classified in
`app.services.data_governance.HARD_DELETABLE_TABLES` as "removed outright"
by the workspace data-deletion endpoint, but no migration ever created a
DELETE policy for it — only `policy_select_members` (0016) and, later,
INSERT/UPDATE policies for the scheduler's own write path (0052). Under
FORCE ROW LEVEL SECURITY, a command with no matching policy silently
matches zero rows rather than erroring, so a deletion request reported
HTTP 200 with `erased_counts["job_schedule"] = 0` while the rows remained
in place — reproduced live against a real database before this fix.

The other two `HARD_DELETABLE_TABLES` entries (`leads`, migration 0034;
`publication_eligibility`, migration 0037) each got an explicit
admin-only DELETE policy at table-creation time; this migration gives
`job_schedule` the same treatment.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0053"
down_revision: str | None = "0052"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "CREATE POLICY job_schedule_delete_roles ON job_schedule "
        "FOR DELETE USING (app_user_has_workspace_role(workspace_id, "
        "ARRAY['admin']::workspace_role[]));"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS job_schedule_delete_roles ON job_schedule;")
