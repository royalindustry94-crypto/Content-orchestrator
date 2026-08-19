"""Pre-publication policy attestations per (content item, platform).

Lumora publishes to third-party platforms whose own policies require
synthetic-media disclosure, original (non-mass-produced) content, and rights
to every input asset. Those requirements cannot be satisfied by generation
code alone, so they are recorded as explicit attestations and enforced before
any publish job may run (see ``app.services.publication_policy``).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, VersionMixin, WorkspaceScopedMixin

# Platforms Lumora is allowed to target. Mirrors the CHECK constraint in
# migration 0037 and the documented control matrix.
SUPPORTED_PLATFORMS = ("youtube", "tiktok", "instagram")


class PublicationEligibility(Base, WorkspaceScopedMixin, VersionMixin):
    __tablename__ = "publication_eligibility"
    __table_args__ = (
        UniqueConstraint(
            "content_item_id",
            "platform",
            name="uq_publication_eligibility_item_platform",
        ),
        Index("ix_publication_eligibility_workspace", "workspace_id"),
        Index(
            "ix_publication_eligibility_fingerprint",
            "workspace_id",
            "platform",
            "originality_fingerprint",
        ),
        Index("ix_publication_eligibility_review_gate", "review_gate_id"),
        Index(
            "ix_publication_eligibility_rights_confirmed_by",
            "rights_confirmed_by",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    content_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("content_items.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    # Provenance of the artifact (model/pipeline identifier).
    generated_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Whether the platform-required AI/synthetic-media disclosure is attached.
    synthetic_media_disclosed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Human rights attestation (who confirmed, and when).
    rights_confirmed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"), nullable=True
    )
    rights_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Deterministic fingerprint of the delivered script, so near-duplicate
    # mass output can be detected per workspace and platform.
    originality_fingerprint: Mapped[str | None] = mapped_column(Text, nullable=True)
    # The approved Human Review Gate that authorises publication.
    review_gate_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("review_gates.id", ondelete="SET NULL"), nullable=True
    )
    policy_notes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
