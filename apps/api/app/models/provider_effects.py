"""provider_effect_keys: durable duplicate-execution guard (WS3).

Before a worker performs a provider-facing side effect for an assignment,
it inserts a key derived from ``assignment_id`` alone (or an explicit
override) — see `app.orchestration.provider_effects.default_effect_key`.
A unique constraint on ``(workspace_id, effect_key)`` makes a second
insert for the *same assignment* a conflict, including across a
crashed-then-recovered attempt (which bumps `attempt_number` but keeps
the same `assignment_id`) — that bump is stored on the row for
audit/debugging but is deliberately not part of the key itself.
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
