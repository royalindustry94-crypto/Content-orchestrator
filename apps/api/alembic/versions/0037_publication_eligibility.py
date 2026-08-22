"""Publication eligibility controls (platform policy, rights, provenance).

Creates ``publication_eligibility``: one row per (content_item, platform)
holding the pre-publication attestations Lumora must have before any content
is handed to a platform API. Enforced in code by
``app.services.publication_policy.assert_publishable``.

The control requirements and their sources (synthetic-media disclosure,
originality/anti-repetition, rights, anti-automation) are recorded in
``docs/PLATFORM_POLICY_CONTROL_MATRIX.md``.

Revision ID: 0037
Revises: 0036
Create Date: 2026-08-19
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
    policy_insert_roles,
    policy_select_members,
    policy_update_roles,
)

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]
# Attestations are compliance statements, so only admins and reviewers may
# create or change them — an editor cannot self-certify rights or disclosure.
_ATTEST = ["admin", "reviewer"]


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE publication_eligibility (
            id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            workspace_id              uuid NOT NULL
                                      REFERENCES workspaces(id) ON DELETE CASCADE,
            content_item_id           uuid NOT NULL
                                      REFERENCES content_items(id) ON DELETE CASCADE,
            platform                  text NOT NULL,
            generated_by              text,
            synthetic_media_disclosed boolean NOT NULL DEFAULT false,
            rights_confirmed_by       uuid REFERENCES profiles(id) ON DELETE SET NULL,
            rights_confirmed_at       timestamptz,
            originality_fingerprint   text,
            review_gate_id            uuid REFERENCES review_gates(id) ON DELETE SET NULL,
            policy_notes              jsonb,
            created_at                timestamptz NOT NULL DEFAULT now(),
            updated_at                timestamptz NOT NULL DEFAULT now(),
            version                   integer NOT NULL DEFAULT 1,
            CONSTRAINT uq_publication_eligibility_item_platform
                UNIQUE (content_item_id, platform),
            CONSTRAINT publication_eligibility_platform_chk CHECK (
                platform IN ('youtube', 'tiktok', 'instagram')
            ),
            -- A rights attestation is either complete (who + when) or absent;
            -- a half-recorded attestation must never satisfy the gate.
            CONSTRAINT publication_eligibility_rights_chk CHECK (
                (rights_confirmed_by IS NULL AND rights_confirmed_at IS NULL)
                OR (rights_confirmed_by IS NOT NULL AND rights_confirmed_at IS NOT NULL)
            )
        );
        """
    )
    op.execute(
        "CREATE INDEX ix_publication_eligibility_workspace "
        "ON publication_eligibility (workspace_id);"
    )
    op.execute(
        "CREATE INDEX ix_publication_eligibility_fingerprint "
        "ON publication_eligibility (workspace_id, platform, originality_fingerprint);"
    )
    # Repository invariant (tests/test_fk_indexes_p1.py): every FK column is
    # indexed.
    op.execute(
        "CREATE INDEX ix_publication_eligibility_review_gate "
        "ON publication_eligibility (review_gate_id);"
    )
    op.execute(
        "CREATE INDEX ix_publication_eligibility_rights_confirmed_by "
        "ON publication_eligibility (rights_confirmed_by);"
    )
    attach_version_trigger("publication_eligibility")
    enable_rls("publication_eligibility")
    # DELETE is granted so an authorised workspace data-deletion request can
    # remove attestations along with the content they describe; the policy
    # below still restricts it to admins.
    grant_runtime("publication_eligibility")
    policy_select_members("publication_eligibility", _ALL)
    policy_insert_roles("publication_eligibility", _ATTEST)
    policy_update_roles("publication_eligibility", _ATTEST)
    op.execute(
        "CREATE POLICY publication_eligibility_delete_roles ON publication_eligibility "
        "FOR DELETE USING (app_user_has_workspace_role(workspace_id, "
        "ARRAY['admin']::workspace_role[]));"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS publication_eligibility;")
