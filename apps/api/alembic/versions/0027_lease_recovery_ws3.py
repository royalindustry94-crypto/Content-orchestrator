"""Milestone 4 Workstream 3: lease management, recovery & worker reliability.

Adds lease bound bookkeeping on stage_assignments, an append-only
stage_recovery_audit ledger, and provider_effect_keys for duplicate
execution prevention. FORCE-RLS on new tables; member-readable,
service-role-written (mirrors stage_claim_audit).

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-27
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_immutable_trigger,
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    # --- lease bound bookkeeping on stage_assignments -------------------------
    op.execute(
        """
        ALTER TABLE stage_assignments
            ADD COLUMN lease_started_at timestamptz,
            ADD COLUMN lease_extension_count integer NOT NULL DEFAULT 0;
        """
    )
    # Active holdings by worker — supports reap_worker_assignments.
    op.execute(
        """
        CREATE INDEX ix_stage_assignments_worker_active
        ON stage_assignments (worker_id)
        WHERE status = ANY (ARRAY[
            'dispatched'::stage_assignment_status,
            'acknowledged'::stage_assignment_status
        ])
        AND worker_id IS NOT NULL;
        """
    )

    # --- recovery enums + audit ledger ----------------------------------------
    op.execute(
        "CREATE TYPE recovery_reason AS ENUM ("
        "'lease_expired','worker_offline','worker_deregistered',"
        "'worker_revoked','worker_restart','max_lease_exceeded');"
    )
    op.execute(
        "CREATE TYPE recovery_outcome AS ENUM ('requeued','dead_lettered','skipped');"
    )
    op.execute(
        """
        CREATE TABLE stage_recovery_audit (
            id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id        uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id       uuid NOT NULL,
            previous_worker_id  uuid,
            reason              recovery_reason NOT NULL,
            previous_status     text NOT NULL,
            previous_attempt    integer NOT NULL,
            new_attempt         integer,
            outcome             recovery_outcome NOT NULL,
            detail              text,
            correlation_id      uuid,
            created_at          timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_stage_recovery_audit_ws_created "
        "ON stage_recovery_audit (workspace_id, created_at);"
    )
    op.execute(
        "CREATE INDEX ix_stage_recovery_audit_assignment "
        "ON stage_recovery_audit (assignment_id, created_at);"
    )
    enable_rls("stage_recovery_audit")
    grant_runtime("stage_recovery_audit", insert=False, update=False, delete=False)
    policy_select_members("stage_recovery_audit", _ALL)
    # Append-only at the DB layer: even the service role cannot UPDATE.
    attach_immutable_trigger("stage_recovery_audit")

    # --- provider effect keys (duplicate-execution guard) ---------------------
    op.execute(
        """
        CREATE TABLE provider_effect_keys (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id     uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            assignment_id    uuid NOT NULL,
            attempt_number   integer NOT NULL,
            effect_key       text NOT NULL,
            effect_kind      text NOT NULL,
            created_at       timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT uq_provider_effect_keys_ws_key UNIQUE (workspace_id, effect_key)
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_provider_effect_keys_assignment "
        "ON provider_effect_keys (assignment_id, attempt_number);"
    )
    enable_rls("provider_effect_keys")
    grant_runtime("provider_effect_keys", insert=False, update=False, delete=False)
    policy_select_members("provider_effect_keys", _ALL)
    attach_immutable_trigger("provider_effect_keys")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS provider_effect_keys;")
    op.execute("DROP TABLE IF EXISTS stage_recovery_audit;")
    op.execute("DROP TYPE IF EXISTS recovery_outcome;")
    op.execute("DROP TYPE IF EXISTS recovery_reason;")
    op.execute("DROP INDEX IF EXISTS ix_stage_assignments_worker_active;")
    op.execute(
        """
        ALTER TABLE stage_assignments
            DROP COLUMN IF EXISTS lease_extension_count,
            DROP COLUMN IF EXISTS lease_started_at;
        """
    )
