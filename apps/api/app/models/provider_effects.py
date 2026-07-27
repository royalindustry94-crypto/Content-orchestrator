"""provider_effect_keys: durable duplicate-execution guard (WS3).

Before a worker performs a provider-facing side effect for an assignment
attempt, it inserts ``{assignment_id}:{attempt_number}`` (or an explicit
override). A unique constraint on ``(workspace_id, effect_key)`` makes a
second insert for the same attempt a conflict — the crashed-then-recovered
path gets a new attempt number and therefore a new key.
"""

from __future__ import annotations

import uuid

from sqlalchemy import Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin, WorkspaceScopedMixin


class ProviderEffectKey(Base, WorkspaceScopedMixin, CreatedAtMixin):
    __tablename__ = "provider_effect_keys"
    __table_args__ = (
        UniqueConstraint("workspace_id", "effect_key", name="uq_provider_effect_keys_ws_key"),
        Index("ix_provider_effect_keys_assignment", "assignment_id", "attempt_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    effect_key: Mapped[str] = mapped_column(Text, nullable=False)
    effect_kind: Mapped[str] = mapped_column(Text, nullable=False)
