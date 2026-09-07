"""Grant app_runtime the write policies content_jobs.py/review_gates.py need
under RLS, so those two routes can move off the owner DB connection.

Revision ID: 0052
Revises: 0051
Create Date: 2026-09-07

TD-072 (2026-09-07 independent audit finding): `content_jobs.py` and
`review_gates.py` are the only two HTTP routes that drive the orchestration
engine (`app.orchestration.controller`), and they use the owner connection
instead of the RLS-scoped runtime session every other tenant route uses,
because the same controller code is also driven by the connectionless
background scheduler with no per-request JWT context. A follow-up audit
traced the complete write surface of `create_content_job()` and
`decide_review_gate()` and found that several tables those functions
write to have no INSERT/UPDATE RLS policy at all for `app_runtime` (they
were only ever written by the owner connection before), or have a policy
whose role list doesn't match what these two routes' own FastAPI guards
already allow (`require_workspace_content_author` = admin/editor;
`require_workspace_reviewer` = admin/reviewer).

This migration only widens/adds RLS policies and two plain GRANTs; it does
not touch the owner connection's access (which was never RLS-restricted)
and does not change what any FastAPI guard allows. The `app_runtime` role
remains `NOBYPASSRLS` throughout. None of these tables are written by any
other route — `research.py`/`strategy.py`/`content_department.py`/
`production.py`/`compliance.py` use their own separate run/audit tables
and never touch `pipeline_runs`, `review_gates`, `job_schedule`,
`workflow_definitions/_stages/_transitions`, `spend_reservations`,
`outbox_events`, or `dead_letter_jobs` — so this cannot regress those
routes' behavior.

Riskiest case (see write-surface audit): `review_gates` and `spend_caps`
are both read with `SELECT ... FOR UPDATE` inside this call graph.
PostgreSQL requires a row to satisfy *both* the SELECT and UPDATE RLS
policies to be visible under a locking read. `review_gates` had no UPDATE
policy at all, and `spend_caps` restricted UPDATE to `admin` only — either
gap alone would silently zero-row `decide_review_gate` or every editor's
`create_content_job` call under RLS. Both are fixed here.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import policy_insert_roles, policy_update_roles  # noqa: E402

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]
_ADMIN_REVIEWER = ["admin", "reviewer"]


def upgrade() -> None:
    # --- plain grants missing outright, independent of RLS -----------------
    op.execute("GRANT UPDATE ON workflow_definitions TO app_runtime;")
    op.execute("GRANT INSERT ON dead_letter_jobs TO app_runtime;")
    # event_consumers carries no workspace_id and RLS is not enabled on it
    # (process-level registry, per its own model docstring) — grant only.
    op.execute("GRANT INSERT ON event_consumers TO app_runtime;")

    # --- pipeline_runs: was SELECT-only ------------------------------------
    policy_insert_roles("pipeline_runs", _EDIT)
    policy_update_roles("pipeline_runs", _ALL)

    # --- spend_reservations: was SELECT-only -------------------------------
    policy_insert_roles("spend_reservations", _EDIT)
    policy_update_roles("spend_reservations", _ALL)

    # --- spend_logs: was SELECT-only ---------------------------------------
    policy_insert_roles("spend_logs", _EDIT)

    # --- job_schedule: was SELECT-only --------------------------------------
    policy_insert_roles("job_schedule", _ALL)
    policy_update_roles("job_schedule", _EDIT)

    # --- review_gates: INSERT excluded editor; UPDATE entirely missing -----
    op.execute("DROP POLICY IF EXISTS review_gates_insert_roles ON review_gates;")
    policy_insert_roles("review_gates", _ALL)
    policy_update_roles("review_gates", _ADMIN_REVIEWER)

    # --- outbox_events: INSERT excluded reviewer; UPDATE entirely missing --
    op.execute("DROP POLICY IF EXISTS outbox_events_insert_roles ON outbox_events;")
    policy_insert_roles("outbox_events", _ALL)
    policy_update_roles("outbox_events", _ALL)

    # --- workflow_definitions/_stages/_transitions: INSERT was admin-only --
    op.execute(
        "DROP POLICY IF EXISTS workflow_definitions_insert_roles ON workflow_definitions;"
    )
    policy_insert_roles("workflow_definitions", _EDIT)
    policy_update_roles("workflow_definitions", _EDIT)  # new capability; grant added above

    op.execute("DROP POLICY IF EXISTS workflow_stages_insert_roles ON workflow_stages;")
    policy_insert_roles("workflow_stages", _EDIT)

    op.execute(
        "DROP POLICY IF EXISTS workflow_transitions_insert_roles ON workflow_transitions;"
    )
    policy_insert_roles("workflow_transitions", _EDIT)

    # --- dead_letter_jobs: grant added above; policy was entirely absent ---
    policy_insert_roles("dead_letter_jobs", _ADMIN_REVIEWER)

    # --- spend_caps: not written by this call graph, but its FOR UPDATE ---
    # --- lock in reserve_spend() needs editor to satisfy the UPDATE policy -
    op.execute("DROP POLICY IF EXISTS spend_caps_update_roles ON spend_caps;")
    policy_update_roles("spend_caps", _EDIT)


def downgrade() -> None:
    # --- spend_caps: restore original admin-only UPDATE policy -------------
    op.execute("DROP POLICY IF EXISTS spend_caps_update_roles ON spend_caps;")
    policy_update_roles("spend_caps", ["admin"])

    # --- dead_letter_jobs ----------------------------------------------------
    op.execute("DROP POLICY IF EXISTS dead_letter_jobs_insert_roles ON dead_letter_jobs;")

    # --- workflow_transitions / _stages / _definitions ----------------------
    op.execute(
        "DROP POLICY IF EXISTS workflow_transitions_insert_roles ON workflow_transitions;"
    )
    policy_insert_roles("workflow_transitions", ["admin"])

    op.execute("DROP POLICY IF EXISTS workflow_stages_insert_roles ON workflow_stages;")
    policy_insert_roles("workflow_stages", ["admin"])

    op.execute("DROP POLICY IF EXISTS workflow_definitions_update_roles ON workflow_definitions;")
    op.execute(
        "DROP POLICY IF EXISTS workflow_definitions_insert_roles ON workflow_definitions;"
    )
    policy_insert_roles("workflow_definitions", ["admin"])

    # --- outbox_events -------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS outbox_events_update_roles ON outbox_events;")
    op.execute("DROP POLICY IF EXISTS outbox_events_insert_roles ON outbox_events;")
    policy_insert_roles("outbox_events", _EDIT)

    # --- review_gates ----------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS review_gates_update_roles ON review_gates;")
    op.execute("DROP POLICY IF EXISTS review_gates_insert_roles ON review_gates;")
    policy_insert_roles("review_gates", _ADMIN_REVIEWER)

    # --- job_schedule ----------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS job_schedule_update_roles ON job_schedule;")
    op.execute("DROP POLICY IF EXISTS job_schedule_insert_roles ON job_schedule;")

    # --- spend_logs --------------------------------------------------------
    op.execute("DROP POLICY IF EXISTS spend_logs_insert_roles ON spend_logs;")

    # --- spend_reservations --------------------------------------------------
    op.execute("DROP POLICY IF EXISTS spend_reservations_update_roles ON spend_reservations;")
    op.execute("DROP POLICY IF EXISTS spend_reservations_insert_roles ON spend_reservations;")

    # --- pipeline_runs -----------------------------------------------------
    op.execute("DROP POLICY IF EXISTS pipeline_runs_update_roles ON pipeline_runs;")
    op.execute("DROP POLICY IF EXISTS pipeline_runs_insert_roles ON pipeline_runs;")

    # --- plain grants --------------------------------------------------------
    op.execute("REVOKE INSERT ON event_consumers FROM app_runtime;")
    op.execute("REVOKE INSERT ON dead_letter_jobs FROM app_runtime;")
    op.execute("REVOKE UPDATE ON workflow_definitions FROM app_runtime;")
