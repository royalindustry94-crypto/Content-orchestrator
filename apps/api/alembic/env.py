from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import model modules here so they register on Base.metadata before
# autogenerate runs.
from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
# Migrations run through the same asyncpg driver as the app itself, so
# there's one code path for "how we talk to Postgres", not two.
_async_url = str(settings.database_url).replace("postgresql://", "postgresql+asyncpg://", 1)
config.set_main_option("sqlalchemy.url", _async_url)

# These indexes are intentionally defined with raw SQL in historical
# migrations (partial predicates, expression ordering, or schema-only
# covering indexes). They are part of the migration-managed schema but are
# not represented by ORM table metadata. Ignore only this explicit allowlist
# when autogenerate sees a reflected index with no metadata counterpart;
# every other schema difference remains visible to `alembic check`.
MIGRATION_MANAGED_INDEXES = frozenset(
    {
        "ix_assets_content_version_id",
        "ix_assets_created_by",
        "ix_assets_updated_by",
        "ix_billing_webhook_events_workspace",
        "ix_content_items_created_by",
        "ix_content_items_current_pipeline_run_id",
        "ix_content_items_current_version_id",
        "ix_content_items_pillar_id",
        "ix_content_items_updated_by",
        "ix_content_lineage_created_by",
        "ix_content_pillars_created_by",
        "ix_content_pillars_updated_by",
        "ix_content_versions_created_by",
        "ix_pipeline_runs_definition_id",
        "ix_pipeline_stage_runs_content_item_id",
        "ix_provider_concurrency_budgets_ws",
        "ix_provider_credentials_created_by",
        "ix_provider_credentials_updated_by",
        "ix_provider_usage_pipeline_stage_run_id",
        "ix_publish_jobs_created_by",
        "ix_publish_jobs_updated_by",
        "ix_review_decisions_content_version_id",
        "ix_review_decisions_reviewer_id",
        "ix_review_gates_decided_by",
        "ix_spend_caps_created_by",
        "ix_spend_caps_updated_by",
        "ix_spend_logs_content_item_id",
        "ix_spend_reservations_content_item_id",
        "ix_stage_assignments_claim_priority",
        "ix_stage_assignments_claimed_by",
        "ix_stage_assignments_provider_inflight",
        "ix_stage_assignments_worker_active",
        "ix_stage_claim_audit_assignment_id",
        "ix_worker_credentials_worker_active",
        "ix_worker_credentials_workspace_id",
        "ix_worker_registry_live",
        "ix_worker_registry_workspace_id",
        "ix_workspace_memberships_user_id",
        "ix_workflow_definitions_created_by",
        "ix_workflow_stages_workspace_id",
        "ix_workflow_transitions_workspace_id",
        "ix_workspaces_created_by",
        "uq_worker_registry_name_instance",
        "ux_spend_reservations_open_run_stage",
    }
)


def include_object(obj, name, type_, reflected, compare_to) -> bool:
    del obj
    if (
        type_ == "index"
        and reflected
        and compare_to is None
        and name in MIGRATION_MANAGED_INDEXES
    ):
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
