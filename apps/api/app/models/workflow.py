"""Workflow definitions: stages, transitions, retry/timeout policy.

Definitions are versioned and immutable per version (amendment: workflow
versioning). A running pipeline_run pins definition_id at start; editing a
workflow creates a new version row rather than mutating an existing one,
so in-flight runs keep deterministic behavior regardless of later edits.
New executions resolve the latest row where is_active=true for a given
name; existing executions never re-resolve — they hold the FK they started
with, which is what preserves deterministic replay.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, Index, Integer, Text, UniqueConstraint, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, CreatedByMixin, WorkspaceScopedMixin
from app.models.enums import ContentStage, WorkflowTransitionTrigger


class WorkflowDefinition(Base, WorkspaceScopedMixin, CreatedAtMixin, CreatedByMixin):
    """One immutable version of a named workflow."""

    __tablename__ = "workflow_definitions"
    __table_args__ = (
        UniqueConstraint("workspace_id", "name", "version", name="uq_workflow_definition_version"),
        Index(
            "ix_workflow_definitions_active",
            "workspace_id",
            "name",
            unique=False,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Only one version per (workspace, name) may be active at a time; a new
    # active version is created by inserting a new row and the app layer
    # (later milestone) flips the previous active row's is_active off in
    # the same transaction. Enforced at the app layer, not a DB constraint,
    # because "at most one active" needs a transaction, not just a check.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WorkflowStage(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """A stage belonging to one definition version. Immutable — stages are
    part of the definition's frozen content.
    """

    __tablename__ = "workflow_stages"
    __table_args__ = (
        UniqueConstraint("definition_id", "stage_key", name="uq_workflow_stage_per_definition"),
        Index("ix_workflow_stages_definition", "definition_id", "ordinal", unique=False),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_key: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    backoff_base_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    backoff_multiplier: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    backoff_max_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=600)
    is_review_gate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_terminal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    compensation_stage_key: Mapped[ContentStage | None] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=True
    )


class WorkflowTransition(Base, WorkspaceScopedMixin, CreatedAtMixin):
    """An edge: from_stage -> to_stage, guarded by trigger + optional
    condition. Immutable, part of the definition's frozen content.
    """

    __tablename__ = "workflow_transitions"
    __table_args__ = (
        Index(
            "ix_workflow_transitions_lookup",
            "definition_id",
            "from_stage",
            "trigger",
            unique=False,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    definition_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workflow_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    from_stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    to_stage: Mapped[ContentStage] = mapped_column(
        SAEnum(ContentStage, name="content_stage", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    trigger: Mapped[WorkflowTransitionTrigger] = mapped_column(
        SAEnum(WorkflowTransitionTrigger, name="workflow_transition_trigger", native_enum=True,
            values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    # Restricted, whitelisted condition expression (not arbitrary code) —
    # e.g. {"field": "content.target_length_seconds", "op": "gt", "value": 60}.
    # Evaluated by app.orchestration.controller's condition evaluator, which
    # only understands this fixed shape, keeping routing deterministic.
    condition: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
