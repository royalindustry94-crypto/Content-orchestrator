"""Milestone 4 Workstream 1: worker identity, credentials, RLS refinement.

- worker_registry gains instance_key, worker_version, drain,
  deregistered_at; capacity/consistency check constraints; idempotent
  registration target (unique name+instance_key).
- worker_credentials: per-worker hashed secrets (design amendment 1 — no
  global machine token). Multiple ACTIVE credentials per worker are
  allowed so rotation is zero-downtime: the old credential stays valid
  until its grace expiry while the new one is already in use.
- RLS refinement (design amendment 2): worker_registry becomes FORCE RLS
  (pinned workers visible to their workspace's members; global workers
  visible to any authenticated user; user roles can never write).
  worker_heartbeats becomes FORCE RLS with SELECT restricted to
  workspace ADMINS of the pinned workspace — operational telemetry stays
  visible to privileged users but not to normal members. Global workers'
  heartbeats are service-role-only until a platform-operator role exists
  (documented limitation, not a silent gap).
- worker_credentials is service-role-only: FORCE RLS with no policies
  and no grants — secret hashes are never readable by user roles.

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-26
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- worker_registry: identity + lifecycle columns ---
    op.execute(
        """
        ALTER TABLE worker_registry
            ADD COLUMN instance_key    text NOT NULL DEFAULT gen_random_uuid()::text,
            ADD COLUMN worker_version  text,
            ADD COLUMN drain           boolean NOT NULL DEFAULT false,
            ADD COLUMN deregistered_at timestamptz;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_worker_registry_name_instance "
        "ON worker_registry (name, instance_key);"
    )
    op.execute(
        """
        ALTER TABLE worker_registry
            ADD CONSTRAINT ck_worker_registry_load_nonneg CHECK (current_load >= 0),
            ADD CONSTRAINT ck_worker_registry_load_capacity CHECK (current_load <= max_concurrency),
            ADD CONSTRAINT ck_worker_registry_max_concurrency CHECK (max_concurrency >= 1),
            ADD CONSTRAINT ck_worker_registry_deregistered_offline CHECK (
                deregistered_at IS NULL
                OR (status = 'offline' AND current_load = 0)
            );
        """
    )
    # Offline-detection sweep touches only rows that could flip.
    op.execute(
        "CREATE INDEX ix_worker_registry_live ON worker_registry (last_heartbeat_at) "
        "WHERE deregistered_at IS NULL AND drain = false;"
    )

    # --- worker_credentials ---
    op.execute("CREATE TYPE worker_credential_status AS ENUM ('active','revoked');")
    op.execute(
        """
        CREATE TABLE worker_credentials (
            id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            worker_id    uuid NOT NULL REFERENCES worker_registry(id) ON DELETE CASCADE,
            workspace_id uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            secret_hash  text NOT NULL,
            status       worker_credential_status NOT NULL DEFAULT 'active',
            created_at   timestamptz NOT NULL DEFAULT now(),
            rotated_at   timestamptz,
            expires_at   timestamptz
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_worker_credentials_worker_active "
        "ON worker_credentials (worker_id) WHERE status = 'active';"
    )
    # Service-role only: FORCE RLS, zero policies, zero grants. Secret
    # hashes must never be readable through any user-facing role.
    op.execute("ALTER TABLE worker_credentials ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE worker_credentials FORCE ROW LEVEL SECURITY;")

    # --- RLS refinement on worker_registry ---
    op.execute("ALTER TABLE worker_registry ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE worker_registry FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY workers_select ON worker_registry
            FOR SELECT
            USING (
                workspace_id IS NULL
                OR is_workspace_member(workspace_id, app_current_user_id())
            );
        """
    )
    # No INSERT/UPDATE/DELETE policies: under FORCE RLS the absence of a
    # policy denies the action for app_runtime even though the M3 GRANTs
    # remain. Worker lifecycle writes go through the service role only.

    # --- RLS refinement on worker_heartbeats (admin-visible telemetry) ---
    op.execute("ALTER TABLE worker_heartbeats ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE worker_heartbeats FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY worker_heartbeats_admin_select ON worker_heartbeats
            FOR SELECT
            USING (
                EXISTS (
                    SELECT 1 FROM worker_registry wr
                    WHERE wr.id = worker_heartbeats.worker_id
                      AND wr.workspace_id IS NOT NULL
                      AND is_workspace_admin(wr.workspace_id, app_current_user_id())
                )
            );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS worker_heartbeats_admin_select ON worker_heartbeats;")
    op.execute("ALTER TABLE worker_heartbeats NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE worker_heartbeats DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS workers_select ON worker_registry;")
    op.execute("ALTER TABLE worker_registry NO FORCE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE worker_registry DISABLE ROW LEVEL SECURITY;")
    op.execute("DROP TABLE IF EXISTS worker_credentials;")
    op.execute("DROP TYPE IF EXISTS worker_credential_status;")
    op.execute("DROP INDEX IF EXISTS ix_worker_registry_live;")
    op.execute(
        """
        ALTER TABLE worker_registry
            DROP CONSTRAINT IF EXISTS ck_worker_registry_deregistered_offline,
            DROP CONSTRAINT IF EXISTS ck_worker_registry_max_concurrency,
            DROP CONSTRAINT IF EXISTS ck_worker_registry_load_capacity,
            DROP CONSTRAINT IF EXISTS ck_worker_registry_load_nonneg;
        """
    )
    op.execute("DROP INDEX IF EXISTS uq_worker_registry_name_instance;")
    op.execute(
        """
        ALTER TABLE worker_registry
            DROP COLUMN IF EXISTS deregistered_at,
            DROP COLUMN IF EXISTS drain,
            DROP COLUMN IF EXISTS worker_version,
            DROP COLUMN IF EXISTS instance_key;
        """
    )
