"""Index Scout and Research Auditor foreign keys.

The repository requires every foreign-key column to have a dedicated index or
a corresponding leading index. These indexes cover ownership, run, source, and
audit traversal paths without changing records or policy behavior.

Revision ID: 0043
Revises: 0042
"""

from __future__ import annotations

from alembic import op

revision = "0043"
down_revision = "0042"
branch_labels = None
depends_on = None

_INDEXES = (
    ("ix_research_runs_created_by", "research_runs", ["created_by"]),
    ("ix_research_runs_updated_by", "research_runs", ["updated_by"]),
    ("ix_research_sources_run", "research_sources", ["research_run_id"]),
    ("ix_opportunities_run", "opportunities", ["research_run_id"]),
    ("ix_opportunities_created_by", "opportunities", ["created_by"]),
    ("ix_opportunities_updated_by", "opportunities", ["updated_by"]),
    ("ix_opportunity_evidence_opportunity", "opportunity_evidence", ["opportunity_id"]),
    ("ix_opportunity_evidence_source", "opportunity_evidence", ["source_id"]),
    ("ix_research_audits_opportunity", "research_audits", ["opportunity_id"]),
    ("ix_research_audits_run", "research_audits", ["research_run_id"]),
    ("ix_research_schedules_created_by", "research_schedules", ["created_by"]),
    ("ix_research_schedules_enabled_by", "research_schedules", ["enabled_by"]),
    ("ix_research_schedules_updated_by", "research_schedules", ["updated_by"]),
)


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)
