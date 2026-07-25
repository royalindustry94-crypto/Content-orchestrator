"""Milestone 3 amendments: idempotency keys, content lineage, asset storage
metadata, extensible provider metadata.

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-21

Additive migration — does not edit 0002-0012. Applies the four CEO-approved
amendments to the content-domain schema.
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
    policy_insert_roles,
    policy_select_members,
)

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_EDIT = ["admin", "editor"]
_ALL = ["admin", "editor", "reviewer"]


def upgrade() -> None:
    # === Amendment 1: idempotency keys ===================================
    # Nullable; unique per workspace when present so retries don't duplicate.
    op.execute("ALTER TABLE pipeline_runs ADD COLUMN idempotency_key text;")
    op.execute(
        "CREATE UNIQUE INDEX uq_pipeline_runs_workspace_idem "
        "ON pipeline_runs (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;"
    )
    op.execute("ALTER TABLE publish_jobs ADD COLUMN idempotency_key text;")
    op.execute(
        "CREATE UNIQUE INDEX uq_publish_jobs_workspace_idem "
        "ON publish_jobs (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;"
    )
    op.execute("ALTER TABLE webhook_events ADD COLUMN idempotency_key text;")
    op.execute(
        "CREATE UNIQUE INDEX uq_webhook_events_workspace_idem "
        "ON webhook_events (workspace_id, idempotency_key) WHERE idempotency_key IS NOT NULL;"
    )

    # === Amendment 3: asset storage metadata ============================
    op.execute(
        """
        ALTER TABLE assets
            ADD COLUMN storage_provider   text,
            ADD COLUMN storage_bucket     text,
            ADD COLUMN storage_object_key text,
            ADD COLUMN checksum           text,
            ADD COLUMN checksum_algorithm text,
            ADD COLUMN mime_type          text,
            ADD COLUMN size_bytes         bigint CHECK (size_bytes IS NULL OR size_bytes >= 0);
        """
    )

    # === Amendment 4: extensible provider metadata ======================
    # provider_metadata is added to pipeline_stage_runs, provider_usage, and
    # spend_logs. Those three carry an immutability trigger, which raises on
    # UPDATE — including the implicit table rewrite ADD COLUMN with a default
    # would attempt. Adding a plain nullable column with NO default is a
    # metadata-only change (no row rewrite), so it does not trip the trigger.
    op.execute("ALTER TABLE pipeline_stage_runs ADD COLUMN provider_metadata jsonb;")
    op.execute("ALTER TABLE provider_usage ADD COLUMN provider_metadata jsonb;")
    op.execute("ALTER TABLE spend_logs ADD COLUMN provider_metadata jsonb;")
    op.execute("ALTER TABLE assets ADD COLUMN provider_metadata jsonb;")

    # === Amendment 2: content lineage ===================================
    op.execute(
        "CREATE TYPE content_lineage_relationship AS ENUM "
        "('translated','remixed','clipped','derived');"
    )
    op.execute(
        """
        CREATE TABLE content_lineage (
            id                     uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id           uuid NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
            parent_content_item_id uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            child_content_item_id  uuid NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
            relationship_type      content_lineage_relationship NOT NULL,
            notes                  text,
            created_at             timestamptz NOT NULL DEFAULT now(),
            created_by             uuid REFERENCES profiles(id),
            CONSTRAINT uq_content_lineage_edge
                UNIQUE (parent_content_item_id, child_content_item_id, relationship_type),
            CONSTRAINT ck_content_lineage_no_self
                CHECK (parent_content_item_id <> child_content_item_id)
        );
        """
    )
    op.execute("CREATE INDEX ix_content_lineage_parent ON content_lineage (parent_content_item_id);")
    op.execute("CREATE INDEX ix_content_lineage_child ON content_lineage (child_content_item_id);")
    op.execute("CREATE INDEX ix_content_lineage_workspace ON content_lineage (workspace_id);")
    # Lineage is immutable history (an edge is a fact); append-only.
    attach_immutable_trigger("content_lineage")
    enable_rls("content_lineage")
    grant_runtime("content_lineage", update=False, delete=False)
    policy_select_members("content_lineage", _ALL)
    policy_insert_roles("content_lineage", _EDIT)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content_lineage;")
    op.execute("DROP TYPE IF EXISTS content_lineage_relationship;")

    op.execute("ALTER TABLE assets DROP COLUMN IF EXISTS provider_metadata;")
    op.execute("ALTER TABLE spend_logs DROP COLUMN IF EXISTS provider_metadata;")
    op.execute("ALTER TABLE provider_usage DROP COLUMN IF EXISTS provider_metadata;")
    op.execute("ALTER TABLE pipeline_stage_runs DROP COLUMN IF EXISTS provider_metadata;")

    op.execute(
        """
        ALTER TABLE assets
            DROP COLUMN IF EXISTS storage_provider,
            DROP COLUMN IF EXISTS storage_bucket,
            DROP COLUMN IF EXISTS storage_object_key,
            DROP COLUMN IF EXISTS checksum,
            DROP COLUMN IF EXISTS checksum_algorithm,
            DROP COLUMN IF EXISTS mime_type,
            DROP COLUMN IF EXISTS size_bytes;
        """
    )

    op.execute("DROP INDEX IF EXISTS uq_webhook_events_workspace_idem;")
    op.execute("ALTER TABLE webhook_events DROP COLUMN IF EXISTS idempotency_key;")
    op.execute("DROP INDEX IF EXISTS uq_publish_jobs_workspace_idem;")
    op.execute("ALTER TABLE publish_jobs DROP COLUMN IF EXISTS idempotency_key;")
    op.execute("DROP INDEX IF EXISTS uq_pipeline_runs_workspace_idem;")
    op.execute("ALTER TABLE pipeline_runs DROP COLUMN IF EXISTS idempotency_key;")
