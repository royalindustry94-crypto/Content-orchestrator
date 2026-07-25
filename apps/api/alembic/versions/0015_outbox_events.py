"""Milestone 4: outbox_events, event_consumers, consumer_checkpoints

Revision ID: 0015
Revises: 0014
Create Date: 2026-07-21
"""
from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import (  # noqa: E402
    attach_version_trigger,
    enable_rls,
    grant_runtime,
    policy_select_members,
)

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ADMIN_EDITOR = ["admin", "editor"]


def upgrade() -> None:
    op.execute("CREATE TYPE outbox_event_status AS ENUM ('pending','dispatched','poison');")
    op.execute(
        """
        CREATE TABLE outbox_events (
            event_id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id      uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            event_type        text NOT NULL,
            event_version     integer NOT NULL DEFAULT 1,
            aggregate_type    text NOT NULL,
            aggregate_id      uuid NOT NULL,
            correlation_id    uuid NOT NULL,
            causation_id      uuid,
            trace_id          text,
            span_id           text,
            sequence          bigint NOT NULL,
            payload           jsonb NOT NULL,
            status            outbox_event_status NOT NULL DEFAULT 'pending',
            delivery_attempts integer NOT NULL DEFAULT 0,
            occurred_at       timestamptz NOT NULL DEFAULT now(),
            produced_by       text NOT NULL,
            version           integer NOT NULL DEFAULT 1,
            updated_at        timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    # Delivery: the relay scans pending events oldest-first.
    op.execute("CREATE INDEX ix_outbox_events_status_time ON outbox_events (status, occurred_at) "
               "WHERE status = 'pending';")
    # Per-aggregate ordering (§3.4 of the design doc).
    op.execute("CREATE UNIQUE INDEX uq_outbox_events_aggregate_sequence "
               "ON outbox_events (aggregate_type, aggregate_id, sequence);")
    op.execute("CREATE INDEX ix_outbox_events_workspace ON outbox_events (workspace_id);")
    # Correlation lookups for tracing/observability.
    op.execute("CREATE INDEX ix_outbox_events_correlation ON outbox_events (correlation_id);")
    attach_version_trigger("outbox_events")
    enable_rls("outbox_events")
    # Written only by domain-writing transactions (any role that writes
    # content), never directly by end users as a standalone action.
    grant_runtime("outbox_events")
    policy_select_members("outbox_events", _ADMIN_EDITOR)

    op.execute(
        """
        CREATE TABLE event_consumers (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            name                   text NOT NULL UNIQUE,
            max_event_version      integer NOT NULL DEFAULT 1,
            max_delivery_attempts  integer NOT NULL DEFAULT 10,
            created_at             timestamptz NOT NULL DEFAULT now(),
            updated_at             timestamptz NOT NULL DEFAULT now(),
            version                integer NOT NULL DEFAULT 1
        );
        """
    )
    attach_version_trigger("event_consumers")
    # Not tenant-scoped (process-level registry) — no RLS/workspace_id;
    # runtime role still needs read access to resolve consumer config.
    op.execute("GRANT SELECT ON event_consumers TO app_runtime;")

    op.execute(
        """
        CREATE TABLE consumer_checkpoints (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consumer_id     uuid NOT NULL REFERENCES event_consumers(id) ON DELETE CASCADE,
            aggregate_type  text NOT NULL,
            partition_key   text NOT NULL,
            last_sequence   bigint NOT NULL DEFAULT 0,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            version         integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_consumer_checkpoint UNIQUE (consumer_id, aggregate_type, partition_key)
        );
        """
    )
    attach_version_trigger("consumer_checkpoints")
    op.execute("GRANT SELECT, INSERT, UPDATE ON consumer_checkpoints TO app_runtime;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS consumer_checkpoints;")
    op.execute("DROP TABLE IF EXISTS event_consumers;")
    op.execute("DROP TABLE IF EXISTS outbox_events;")
    op.execute("DROP TYPE IF EXISTS outbox_event_status;")
