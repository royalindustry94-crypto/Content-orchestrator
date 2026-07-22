"""Milestone 3 shared helpers: version trigger, immutability trigger, role check

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-21
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_version_and_updated_at() RETURNS trigger AS $$
        BEGIN
            NEW.version := OLD.version + 1;
            NEW.updated_at := now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_update() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is immutable; row updates are not permitted', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_user_has_workspace_role(
            p_workspace_id uuid, p_roles workspace_role[]
        ) RETURNS boolean AS $$
            SELECT EXISTS (
                SELECT 1 FROM workspace_memberships m
                WHERE m.workspace_id = p_workspace_id
                  AND m.user_id = app_current_user_id()
                  AND m.role = ANY(p_roles)
            )
        $$ LANGUAGE sql STABLE;
        """
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION app_user_has_workspace_role(uuid, workspace_role[]) TO app_runtime;"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app_user_has_workspace_role(uuid, workspace_role[]);")
    op.execute("DROP FUNCTION IF EXISTS prevent_update();")
    op.execute("DROP FUNCTION IF EXISTS set_version_and_updated_at();")
