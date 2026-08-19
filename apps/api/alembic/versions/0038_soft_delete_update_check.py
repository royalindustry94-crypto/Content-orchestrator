"""Make soft delete reachable under RLS (tombstone writes were impossible).

The four tables carrying ``deleted_at`` (``content_items``, ``assets``,
``publish_jobs``, ``content_pillars``) could never have that column set through
the application runtime role. Reproduced before this migration, with a real
workspace-admin identity on the RLS-bound role:

    UPDATE content_items SET updated_by = updated_by ...   -> 1 row
    UPDATE content_items SET deleted_at = now() ...        -> ERROR
        new row violates row-level security policy for table "content_items"

Root cause, isolated by experiment: these tables are FORCE ROW LEVEL SECURITY,
and their SELECT policy carries ``deleted_at IS NULL``. PostgreSQL validates
the row produced by an UPDATE against the applicable policies, so the moment a
row is tombstoned it becomes invisible and the write is refused. Recreating
only the SELECT policy without the ``deleted_at IS NULL`` predicate (inside a
rolled-back transaction) made the identical UPDATE succeed, which confirms the
predicate — not the role check — was the blocker.

This migration changes the SELECT policies so that:

* every role that could previously read live rows still reads live rows;
* withdrawn (tombstoned) rows are additionally visible **only** to admins and
  editors of the owning workspace, who are exactly the roles already permitted
  to write these tables;
* reviewers and every other tenant still cannot see withdrawn rows.

It also states an explicit WITH CHECK on the UPDATE policies so the update
contract is declared rather than inherited. RLS remains enabled and forced, no
grant is widened, and no earlier migration is edited or renumbered.

Product read paths are unaffected: the services that display content
(``operations_dashboard``, ``operations_mission``, ``operations_v4``) already
filter ``deleted_at IS NULL`` in their own queries, and the partial unique
indexes remain scoped to live rows.

Revision ID: 0038
Revises: 0037
"""

from __future__ import annotations

from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None

_WRITE_ROLES = "ARRAY['admin','editor']::workspace_role[]"

# table -> roles allowed to read live rows (unchanged from the original policy)
_SELECT_ROLES: dict[str, str] = {
    "content_items": "ARRAY['admin','editor','reviewer']::workspace_role[]",
    "assets": "ARRAY['admin','editor','reviewer']::workspace_role[]",
    "publish_jobs": "ARRAY['admin','editor','reviewer']::workspace_role[]",
    "content_pillars": "ARRAY['admin','editor','reviewer']::workspace_role[]",
}


def upgrade() -> None:
    for table, read_roles in _SELECT_ROLES.items():
        # Live rows: unchanged audience. Withdrawn rows: writers only.
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(
            f"CREATE POLICY {table}_select_member ON {table} FOR SELECT USING ("
            f"  (deleted_at IS NULL "
            f"   AND app_user_has_workspace_role(workspace_id, {read_roles})) "
            f"  OR (deleted_at IS NOT NULL "
            f"      AND app_user_has_workspace_role(workspace_id, {_WRITE_ROLES}))"
            f");"
        )

        # Declare the update contract explicitly for both old and new row.
        op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
        op.execute(
            f"CREATE POLICY {table}_update_roles ON {table} FOR UPDATE "
            f"USING (app_user_has_workspace_role(workspace_id, {_WRITE_ROLES})) "
            f"WITH CHECK (app_user_has_workspace_role(workspace_id, {_WRITE_ROLES}));"
        )


def downgrade() -> None:
    for table, read_roles in _SELECT_ROLES.items():
        op.execute(f"DROP POLICY IF EXISTS {table}_select_member ON {table};")
        op.execute(
            f"CREATE POLICY {table}_select_member ON {table} FOR SELECT "
            f"USING (deleted_at IS NULL "
            f"       AND app_user_has_workspace_role(workspace_id, {read_roles}));"
        )
        op.execute(f"DROP POLICY IF EXISTS {table}_update_roles ON {table};")
        op.execute(
            f"CREATE POLICY {table}_update_roles ON {table} FOR UPDATE "
            f"USING (app_user_has_workspace_role(workspace_id, {_WRITE_ROLES}));"
        )
