"""Milestone 4: worker_registry, worker_heartbeats

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-21
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE worker_status AS ENUM ('online','busy','draining','offline');")

    # Not workspace-scoped: a worker may serve multiple/all workspaces.
    # workspace_id is a nullable pin, not a tenant-isolation boundary, so
    # this table intentionally has NO RLS — worker registry membership is
    # an operational/admin concern, not tenant data. Read access is
    # granted broadly to app_runtime; write access is restricted to the
    # (future) worker-registration service path, not end-user roles.
    op.execute(
        """
        CREATE TABLE worker_registry (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid REFERENCES workspaces(id) ON DELETE CASCADE,
            name              text NOT NULL,
            supported_stages  text[] NOT NULL DEFAULT '{}',
            capabilities      jsonb,
            status            worker_status NOT NULL DEFAULT 'offline',
            max_concurrency   integer NOT NULL DEFAULT 1,
            current_load      integer NOT NULL DEFAULT 0,
            health_score      integer NOT NULL DEFAULT 100 CHECK (health_score BETWEEN 0 AND 100),
            last_heartbeat_at timestamptz,
            registered_at     timestamptz NOT NULL DEFAULT now(),
            created_at        timestamptz NOT NULL DEFAULT now(),
            updated_at        timestamptz NOT NULL DEFAULT now(),
            version           integer NOT NULL DEFAULT 1
        );
        """
    )
    # Dispatcher's core query: eligible workers for a stage.
    op.execute("CREATE INDEX ix_worker_registry_status ON worker_registry (status) "
               "WHERE status IN ('online','busy');")
    op.execute("CREATE INDEX ix_worker_registry_stages ON worker_registry USING GIN (supported_stages);")
    op.execute(
        "CREATE TRIGGER trg_worker_registry_version BEFORE UPDATE ON worker_registry "
        "FOR EACH ROW EXECUTE FUNCTION set_version_and_updated_at();"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON worker_registry TO app_runtime;")

    op.execute(
        """
        CREATE TABLE worker_heartbeats (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            worker_id     uuid NOT NULL REFERENCES worker_registry(id) ON DELETE CASCADE,
            status        worker_status NOT NULL,
            current_load  integer NOT NULL DEFAULT 0,
            heartbeat_at  timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    op.execute("CREATE INDEX ix_worker_heartbeats_worker_time ON worker_heartbeats (worker_id, heartbeat_at DESC);")
    op.execute("GRANT SELECT, INSERT ON worker_heartbeats TO app_runtime;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS worker_heartbeats;")
    op.execute("DROP TABLE IF EXISTS worker_registry;")
    op.execute("DROP TYPE IF EXISTS worker_status;")
