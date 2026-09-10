"""Widen review_gates UPDATE RLS to include editor.

Revision ID: 0056
Revises: 0055
Create Date: 2026-09-10

Independent-audit finding on PR #109 (issue #108, pre-approval content
editing): `content_desk.edit_review_gate_content` is gated at the
FastAPI layer by `require_workspace_content_author` (admin/editor), and
performs a `SELECT ... FOR UPDATE` on `review_gates` before writing
`gate.content_version_id`. Migration 0052 set `review_gates`'s UPDATE
policy to admin/reviewer only (it was scoped to what `decide_review_gate`
needed at the time, before an edit path existed). PostgreSQL requires a
row to satisfy *both* the SELECT and UPDATE RLS policies to be visible
under a locking read, so an editor's PATCH request — correctly admitted
by the FastAPI guard — was silently zero-rowed by RLS and returned a
spurious 404 instead of ever editing anything.

This widens the UPDATE policy to admin/editor/reviewer (the union of
what `decide_review_gate` and `edit_review_gate_content` each need),
matching the table's own INSERT policy (already admin/editor/reviewer
since migration 0052). FastAPI-level guards continue to be the actual
authorization boundary for *which* columns each role may change
(`require_workspace_reviewer` for status/decided_at/decided_by,
`require_workspace_content_author` for content_version_id) — this
migration only ensures RLS does not silently hide the row for either
guard's own admitted role, the same reasoning migration 0052 documents
for this exact table.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

from alembic import op

sys.path.append(str(Path(__file__).resolve().parents[1]))
from migration_helpers import policy_update_roles  # noqa: E402

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ALL = ["admin", "editor", "reviewer"]
_ADMIN_REVIEWER = ["admin", "reviewer"]


def upgrade() -> None:
    op.execute("DROP POLICY IF EXISTS review_gates_update_roles ON review_gates;")
    policy_update_roles("review_gates", _ALL)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS review_gates_update_roles ON review_gates;")
    policy_update_roles("review_gates", _ADMIN_REVIEWER)
