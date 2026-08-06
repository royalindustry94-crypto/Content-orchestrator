"""P-006 / TD-021: covering indexes for foreign-key columns.

Revision ID: 0031_fk
Revises: 0030
Create Date: 2026-07-28

Adds btree indexes on FK columns that lacked a leading-column index,
so ON DELETE / join plans do not fall back to sequential scans.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_fk"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index_name, table, column) — only FKs that had no leading-column index
# at the time of the P-006 probe on the P0 baseline schema.
_INDEXES: tuple[tuple[str, str, str], ...] = (
    ("ix_workspaces_created_by", "workspaces", "created_by"),
    ("ix_workspace_memberships_user_id", "workspace_memberships", "user_id"),
    ("ix_content_pillars_created_by", "content_pillars", "created_by"),
    ("ix_content_pillars_updated_by", "content_pillars", "updated_by"),
    ("ix_spend_caps_created_by", "spend_caps", "created_by"),
    ("ix_spend_caps_updated_by", "spend_caps", "updated_by"),
    ("ix_provider_credentials_created_by", "provider_credentials", "created_by"),
    ("ix_provider_credentials_updated_by", "provider_credentials", "updated_by"),
    ("ix_content_items_created_by", "content_items", "created_by"),
    ("ix_content_items_updated_by", "content_items", "updated_by"),
    ("ix_content_items_pillar_id", "content_items", "pillar_id"),
    ("ix_content_items_current_pipeline_run_id", "content_items", "current_pipeline_run_id"),
    ("ix_content_items_current_version_id", "content_items", "current_version_id"),
    ("ix_content_versions_created_by", "content_versions", "created_by"),
    ("ix_pipeline_runs_definition_id", "pipeline_runs", "definition_id"),
    ("ix_pipeline_stage_runs_content_item_id", "pipeline_stage_runs", "content_item_id"),
    ("ix_assets_content_version_id", "assets", "content_version_id"),
    ("ix_assets_created_by", "assets", "created_by"),
    ("ix_assets_updated_by", "assets", "updated_by"),
    ("ix_publish_jobs_created_by", "publish_jobs", "created_by"),
    ("ix_publish_jobs_updated_by", "publish_jobs", "updated_by"),
    ("ix_review_decisions_content_version_id", "review_decisions", "content_version_id"),
    ("ix_review_decisions_reviewer_id", "review_decisions", "reviewer_id"),
    ("ix_spend_logs_content_item_id", "spend_logs", "content_item_id"),
    ("ix_spend_reservations_content_item_id", "spend_reservations", "content_item_id"),
    ("ix_provider_usage_pipeline_stage_run_id", "provider_usage", "pipeline_stage_run_id"),
    ("ix_content_lineage_created_by", "content_lineage", "created_by"),
    ("ix_workflow_definitions_created_by", "workflow_definitions", "created_by"),
    ("ix_workflow_stages_workspace_id", "workflow_stages", "workspace_id"),
    ("ix_workflow_transitions_workspace_id", "workflow_transitions", "workspace_id"),
    ("ix_worker_registry_workspace_id", "worker_registry", "workspace_id"),
    ("ix_stage_assignments_claimed_by", "stage_assignments", "claimed_by"),
    ("ix_review_gates_decided_by", "review_gates", "decided_by"),
    ("ix_worker_credentials_workspace_id", "worker_credentials", "workspace_id"),
    ("ix_stage_claim_audit_assignment_id", "stage_claim_audit", "assignment_id"),
)


def upgrade() -> None:
    for name, table, column in _INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({column});")


def downgrade() -> None:
    for name, _table, _column in reversed(_INDEXES):
        op.execute(f"DROP INDEX IF EXISTS {name};")
