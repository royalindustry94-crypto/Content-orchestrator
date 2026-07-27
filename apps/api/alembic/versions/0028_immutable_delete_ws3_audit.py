"""Milestone 4 Workstream 3 audit hardening: append-only DELETE guard.

Adds prevent_delete() and attaches it to stage_recovery_audit and
provider_effect_keys so even the table owner cannot erase recovery /
effect history (UPDATE already blocked by prevent_update from 0027).

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-27
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import attach_immutable_delete_trigger  # noqa: E402

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_delete() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'table % is immutable; row deletes are not permitted', TG_TABLE_NAME
                USING ERRCODE = 'restrict_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    attach_immutable_delete_trigger("stage_recovery_audit")
    attach_immutable_delete_trigger("provider_effect_keys")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_stage_recovery_audit_immutable_delete ON stage_recovery_audit;")
    op.execute("DROP TRIGGER IF EXISTS trg_provider_effect_keys_immutable_delete ON provider_effect_keys;")
    op.execute("DROP FUNCTION IF EXISTS prevent_delete();")
