"""stage_claim_audit: an append-only ledger of every worker claim attempt
(WS2). Workspace-owned, FORCE-RLS, member-readable, service-role-written —
so an operator can see who claimed what and why a claim was refused,
without any client being able to forge or read another workspace's ledger.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, WorkspaceScopedMixin
from app.models.enums import ClaimOutcome, ContentStage


class StageClaimAudit(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "stage_claim_audit"
    __table_args__ = (
        Index("ix_stage_claim_audit_ws_created", "workspace_id", "created_at"),
        Index("ix_stage_claim_audit_worker", "worker_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("stage_assignments.id", ondelete="SET NULL"),
        nullable=True,
    )
    worker_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("worker_registry.id"), nullable=False
    )
    outcome: Mapped[ClaimOutcome] = mapped_column(
        SAEnum(
            ClaimOutcome,
            name="claim_outcome",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=False,
    )
    stage: Mapped[ContentStage | None] = mapped_column(
        SAEnum(
            ContentStage,
            name="content_stage",
            native_enum=True,
            values_callable=lambda obj: [e.value for e in obj],
        ),
        nullable=True,
    )
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
