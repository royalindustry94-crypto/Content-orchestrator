"""Persist five-step content profiles and close remaining public-table RLS gaps.

Revision ID: 0052
Revises: 0051
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workspace_content_profiles",
        sa.Column(
            "workspace_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("service_mode", sa.String(length=16), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("offer", sa.Text(), nullable=False),
        sa.Column("target_audience", sa.Text(), nullable=False),
        sa.Column("brand_voice", sa.Text(), nullable=False),
        sa.Column("target_platform", sa.String(length=80), nullable=False),
        sa.Column("content_goal", sa.Text(), nullable=False),
        sa.Column("default_length_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "service_mode IN ('own', 'client')", name="ck_content_profile_service_mode"
        ),
        sa.CheckConstraint(
            "default_length_seconds BETWEEN 1 AND 3600",
            name="ck_content_profile_default_length",
        ),
    )
    op.create_index(
        "ix_workspace_content_profiles_created_by",
        "workspace_content_profiles",
        ["created_by"],
    )
    op.create_index(
        "ix_workspace_content_profiles_updated_by",
        "workspace_content_profiles",
        ["updated_by"],
    )
    op.execute("ALTER TABLE workspace_content_profiles ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE workspace_content_profiles FORCE ROW LEVEL SECURITY;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON workspace_content_profiles TO app_runtime;")
    op.execute(
        """
        CREATE POLICY workspace_content_profiles_select_member
        ON workspace_content_profiles FOR SELECT
        USING (app_user_has_workspace_role(
            workspace_id,
            ARRAY['admin','editor','reviewer']::workspace_role[]
        ));
        """
    )
    op.execute(
        """
        CREATE POLICY workspace_content_profiles_insert_author
        ON workspace_content_profiles FOR INSERT
        WITH CHECK (app_user_has_workspace_role(
            workspace_id,
            ARRAY['admin','editor']::workspace_role[]
        ));
        """
    )
    op.execute(
        """
        CREATE POLICY workspace_content_profiles_update_author
        ON workspace_content_profiles FOR UPDATE
        USING (app_user_has_workspace_role(
            workspace_id,
            ARRAY['admin','editor']::workspace_role[]
        ))
        WITH CHECK (app_user_has_workspace_role(
            workspace_id,
            ARRAY['admin','editor']::workspace_role[]
        ));
        """
    )
    op.execute(
        """
        CREATE POLICY workspace_content_profiles_delete_admin
        ON workspace_content_profiles FOR DELETE
        USING (app_user_has_workspace_role(
            workspace_id,
            ARRAY['admin']::workspace_role[]
        ));
        """
    )

    # These process/auth metadata tables intentionally remain unavailable to
    # browser API roles. RLS removes Supabase advisor gaps; owner sessions keep
    # migration/auth access, while the two runtime tables get narrow policies.
    for table in (
        "alembic_version",
        "local_auth_credentials",
        "event_consumers",
        "consumer_checkpoints",
    ):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
    op.execute(
        "CREATE POLICY event_consumers_runtime_select ON event_consumers "
        "FOR SELECT TO app_runtime USING (true);"
    )
    op.execute(
        "CREATE POLICY consumer_checkpoints_runtime_select ON consumer_checkpoints "
        "FOR SELECT TO app_runtime USING (true);"
    )
    op.execute(
        "CREATE POLICY consumer_checkpoints_runtime_insert ON consumer_checkpoints "
        "FOR INSERT TO app_runtime WITH CHECK (true);"
    )
    op.execute(
        "CREATE POLICY consumer_checkpoints_runtime_update ON consumer_checkpoints "
        "FOR UPDATE TO app_runtime USING (true) WITH CHECK (true);"
    )


def downgrade() -> None:
    op.execute(
        "DROP POLICY IF EXISTS consumer_checkpoints_runtime_update "
        "ON consumer_checkpoints;"
    )
    op.execute(
        "DROP POLICY IF EXISTS consumer_checkpoints_runtime_insert "
        "ON consumer_checkpoints;"
    )
    op.execute(
        "DROP POLICY IF EXISTS consumer_checkpoints_runtime_select "
        "ON consumer_checkpoints;"
    )
    op.execute(
        "DROP POLICY IF EXISTS event_consumers_runtime_select ON event_consumers;"
    )
    op.execute("ALTER TABLE consumer_checkpoints DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE event_consumers DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE local_auth_credentials DISABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE alembic_version DISABLE ROW LEVEL SECURITY;")
    op.drop_table("workspace_content_profiles")
