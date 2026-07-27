"""stage_recovery_audit: append-only ledger of every lease/worker recovery
action (WS3). Workspace-owned, FORCE-RLS, member-readable, service-role-
written and DB-immutable — parallel to stage_claim_audit.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Index, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, WorkspaceScopedMixin
from app.models.enums import RecoveryOutcome, RecoveryReason


class StageRecoveryAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "stage_recovery_audit"
    __table_args__ = (
        Index("ix_stage_recovery_audit_ws_created", "workspace_id", "created_at"),
        Index("ix_stage_recovery_audit_assignment", "assignment_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_worker_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    reason: Mapped[RecoveryReason] = mapped_column(
        SAEnum(
            RecoveryReason,
            name="recovery_reason",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    previous_status: Mapped[str] = mapped_column(Text, nullable=False)
    previous_attempt: Mapped[int] = mapped_column(Integer, nullable=False)
    new_attempt: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[RecoveryOutcome] = mapped_column(
        SAEnum(
            RecoveryOutcome,
            name="recovery_outcome",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
