"""Grant app_runtime the admin-scoped read/write access the Operations
Dashboard's 21 non-compliant handlers need, so operations_dashboard.py can
move off the owner DB connection.

Revision ID: 0054
Revises: 0053
Create Date: 2026-09-08

TD-082 (2026-09-08 write-surface audit): `apps/api/app/api/routes/
operations_dashboard.py` uses the owner connection (`AsyncSessionLocal`)
in 21 of its 28 handlers instead of the RLS-scoped runtime session every
other tenant route uses — the same architectural gap TD-072 (migration
0052) closed for `content_jobs.py`/`review_gates.py`. All 21 handlers gate
exclusively on `require_workspace_admin`, so every policy added here is
scoped to `admin` only (narrower than 0052's `_EDIT`/`_ALL`, which needed
editor/reviewer too).

Two genuinely blocking gaps, not just "silently zero rows":

- `billing_webhook_events` has RLS enabled but was never given `app_runtime`
  any grant at all (migration 0031, deliberately owner-connection-only for
  Stripe webhook ingest). Nine of the 21 handlers read it (directly, or via
  `operations_dashboard.customers()`/`operations_mission._build_alerts()`).
  Under the RLS session this is `permission denied`, a hard 500, not an
  empty result.
- `worker_credentials` has FORCE RLS with zero policies AND zero grants at
  all (migration 0025, explicitly "service-role-only ... secret hashes are
  never readable by user roles"). `action_emergency_stop` both reads and
  revokes credentials.

One `SELECT ... FOR UPDATE` risk, the same class of bug TD-072's own
write-surface audit found and fixed: `action_emergency_stop` reaches
`app.orchestration.recovery.reap_worker_assignments()`, which locks
`stage_assignments` rows with `.with_for_update(skip_locked=True)` and
then mutates them — `stage_assignments` had a SELECT policy (0018) but no
UPDATE policy, which under Postgres RLS means the FOR UPDATE lock silently
matches zero rows rather than erroring. Same recovery path also locks and
updates `worker_registry` via `_release_worker_slot()`.

Explicit decision on `worker_registry`/`worker_credentials` (see the
migration's own comment block below and TD-082's write-surface audit):
`action_pause_workers`/`action_resume_workers`/`action_emergency_stop` are
Founder/admin "Quick Actions" already shipped and reachable via the HTTP
API today (gated by `require_workspace_admin`, currently over the owner
connection). Migration 0025's "user roles can never write worker_registry"
intent was about arbitrary editor/reviewer access to system-owned worker
infrastructure, not about denying the product's own already-shipped admin
actions a second line of defense. Widening RLS here does not grant an
admin any capability they don't already have through the existing route —
it only makes that already-permitted write pass through the database's
tenant boundary instead of relying solely on the Python query's own
`WHERE` clause, which is exactly what TD-082 exists to fix. The addition
is deliberately narrow: workspace-pinned rows only (`workspace_id IS NOT
NULL`), so globally-shared workers (`workspace_id IS NULL`, the M4
reference-client default) remain untouchable by any workspace admin,
preserving 0025's original boundary for the one case it was actually
protecting.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import policy_select_members, policy_update_roles  # noqa: E402

revision: str = "0054"
down_revision: str | None = "0053"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADMIN = ["admin"]


def upgrade() -> None:
    # --- billing_webhook_events: was owner-connection-only, zero app_runtime
    # access at all (not even a grant) ------------------------------------
    op.execute("GRANT SELECT ON billing_webhook_events TO app_runtime;")
    policy_select_members("billing_webhook_events", _ADMIN)

    # --- dead_letter_jobs: SELECT (0012) + INSERT (0052) existed; UPDATE
    # never added — action_retry_failed_jobs/action_clear_dead_letter both
    # mutate entry.status on an existing row -------------------------------
    op.execute("GRANT UPDATE ON dead_letter_jobs TO app_runtime;")
    policy_update_roles("dead_letter_jobs", _ADMIN)

    # --- stage_assignments: SELECT-only since 0018 (grant_runtime() already
    # granted full CRUD at the SQL level); UPDATE policy needed for the
    # SELECT ... FOR UPDATE path inside reap_worker_assignments() ----------
    policy_update_roles("stage_assignments", _ADMIN)

    # --- stage_recovery_audit: grant explicitly excluded INSERT (0027).
    # This is an audit/compliance trail, so the WITH CHECK deliberately
    # goes beyond the plain policy_insert_roles() helper: it also requires
    # assignment_id to reference a real stage_assignments row in the same
    # workspace, not just "workspace_id names a workspace I administer" —
    # otherwise an admin could insert fabricated recovery-audit rows for
    # assignment_ids that don't exist at all. The real caller
    # (recover_assignment()'s _audit() helper) always inserts a row whose
    # assignment_id/workspace_id already match a genuine locked
    # stage_assignments row, so this is a no-op restriction for the actual
    # application code path. ------------------------------------------
    op.execute("GRANT INSERT ON stage_recovery_audit TO app_runtime;")
    op.execute(
        "CREATE POLICY stage_recovery_audit_insert_roles ON stage_recovery_audit "
        "FOR INSERT WITH CHECK ("
        "app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]) "
        "AND EXISTS (SELECT 1 FROM stage_assignments sa WHERE sa.id = assignment_id "
        "AND sa.workspace_id = stage_recovery_audit.workspace_id));"
    )

    # --- worker_registry: GRANT already exists (0017: SELECT/INSERT/UPDATE);
    # only a matching UPDATE policy was missing. workspace_id IS NOT NULL
    # guard preserves 0025's "globally-shared workers stay untouchable"
    # boundary — see module docstring. -------------------------------------
    op.execute(
        "CREATE POLICY worker_registry_update_admin ON worker_registry FOR UPDATE "
        "USING (workspace_id IS NOT NULL AND "
        "app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));"
    )

    # --- worker_credentials: zero grant, zero policy (0025: service-role-
    # only). workspace_id is NOT NULL on this table (every credential
    # belongs to exactly one workspace via its worker), so no extra guard
    # is needed the way worker_registry's nullable column required. -------
    op.execute("GRANT SELECT, UPDATE ON worker_credentials TO app_runtime;")
    op.execute(
        "CREATE POLICY worker_credentials_admin_select ON worker_credentials FOR SELECT "
        "USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));"
    )
    op.execute(
        "CREATE POLICY worker_credentials_admin_update ON worker_credentials FOR UPDATE "
        "USING (app_user_has_workspace_role(workspace_id, ARRAY['admin']::workspace_role[]));"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS worker_credentials_admin_update ON worker_credentials;"
    )
    op.execute(
        "DROP POLICY IF EXISTS worker_credentials_admin_select ON worker_credentials;"
    )
    op.execute("REVOKE SELECT, UPDATE ON worker_credentials FROM app_runtime;")

    op.execute("DROP POLICY IF EXISTS worker_registry_update_admin ON worker_registry;")

    op.execute("DROP POLICY IF EXISTS stage_recovery_audit_insert_roles ON stage_recovery_audit;")
    op.execute("REVOKE INSERT ON stage_recovery_audit FROM app_runtime;")

    op.execute("DROP POLICY IF EXISTS stage_assignments_update_roles ON stage_assignments;")

    op.execute("DROP POLICY IF EXISTS dead_letter_jobs_update_roles ON dead_letter_jobs;")
    op.execute("REVOKE UPDATE ON dead_letter_jobs FROM app_runtime;")

    op.execute("DROP POLICY IF EXISTS billing_webhook_events_select_member ON billing_webhook_events;")
    op.execute("REVOKE SELECT ON billing_webhook_events FROM app_runtime;")
