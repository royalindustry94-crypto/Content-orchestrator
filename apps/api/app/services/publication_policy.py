"""Fail-closed pre-publication gate.

No content may be handed to a platform API unless every control below is
satisfied. The checks exist because the target platforms' own published
policies require them (see ``docs/PLATFORM_POLICY_CONTROL_MATRIX.md``):

1. **Approved Human Review Gate** — publication is never automatic. This also
   prevents "publish anyway" behaviour when approval is missing or a gate was
   rejected, timed out, or is still awaiting a decision.
2. **Synthetic-media disclosure** — the platforms require AI/synthetic content
   to be disclosed; an undisclosed artifact is not publishable.
3. **Rights attestation** — a named human must have confirmed the workspace
   holds rights to the inputs, with a timestamp.
4. **Originality / anti-repetition** — a fingerprint is required, and a
   near-identical fingerprint already published to the same platform in the
   same workspace blocks the publish (mass-produced repetitive output).
5. **Supported platform** — an unrecognised target is refused rather than
   attempted.

Every refusal raises ``PublicationBlocked`` carrying a stable ``code`` so the
caller can surface the reason; nothing is auto-approved on failure.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ReviewGateStatus
from app.models.publication_policy import SUPPORTED_PLATFORMS, PublicationEligibility
from app.models.review_gate import ReviewGate


class PublicationBlocked(Exception):
    """Raised when a publication attempt fails a mandatory control."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PublicationDecision:
    content_item_id: uuid.UUID
    platform: str
    eligibility_id: uuid.UUID
    review_gate_id: uuid.UUID


def fingerprint_script(*parts: str | None) -> str:
    """Stable fingerprint of the delivered script text.

    Normalised (case, whitespace) so trivial edits do not defeat the
    anti-repetition control.
    """
    normalized = " ".join(
        " ".join((part or "").lower().split()) for part in parts
    ).strip()
    if not normalized:
        raise PublicationBlocked(
            "originality_fingerprint_missing",
            "cannot fingerprint empty script content",
        )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def assert_publishable(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    content_item_id: uuid.UUID,
    platform: str,
) -> PublicationDecision:
    """Return the decision, or raise ``PublicationBlocked``. Never auto-approves."""
    normalized_platform = (platform or "").strip().lower()
    if normalized_platform not in SUPPORTED_PLATFORMS:
        raise PublicationBlocked(
            "unsupported_platform",
            f"platform {platform!r} is not an approved publication target",
        )

    row = (
        await session.execute(
            select(PublicationEligibility).where(
                PublicationEligibility.workspace_id == workspace_id,
                PublicationEligibility.content_item_id == content_item_id,
                PublicationEligibility.platform == normalized_platform,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise PublicationBlocked(
            "eligibility_missing",
            "no publication eligibility record exists for this item and platform",
        )

    if row.review_gate_id is None:
        raise PublicationBlocked(
            "review_gate_missing",
            "publication requires an approved human review gate",
        )
    gate = await session.get(ReviewGate, row.review_gate_id)
    if gate is None or gate.workspace_id != workspace_id:
        raise PublicationBlocked(
            "review_gate_missing",
            "the referenced review gate does not exist in this workspace",
        )
    if gate.status != ReviewGateStatus.APPROVED:
        raise PublicationBlocked(
            "review_gate_not_approved",
            f"review gate status is {gate.status.value!r}; publication requires 'approved'",
        )

    if not row.synthetic_media_disclosed:
        raise PublicationBlocked(
            "synthetic_media_not_disclosed",
            "platform policy requires AI/synthetic-media disclosure before publishing",
        )

    if row.rights_confirmed_by is None or row.rights_confirmed_at is None:
        raise PublicationBlocked(
            "rights_not_confirmed",
            "a named reviewer must confirm content rights before publishing",
        )

    if not row.originality_fingerprint:
        raise PublicationBlocked(
            "originality_fingerprint_missing",
            "an originality fingerprint is required before publishing",
        )

    duplicate = (
        await session.execute(
            select(PublicationEligibility.content_item_id).where(
                PublicationEligibility.workspace_id == workspace_id,
                PublicationEligibility.platform == normalized_platform,
                PublicationEligibility.originality_fingerprint
                == row.originality_fingerprint,
                PublicationEligibility.content_item_id != content_item_id,
            )
        )
    ).first()
    if duplicate is not None:
        raise PublicationBlocked(
            "duplicate_content_for_platform",
            "identical content was already prepared for this platform in this "
            "workspace; repetitive mass output is not publishable",
        )

    return PublicationDecision(
        content_item_id=content_item_id,
        platform=normalized_platform,
        eligibility_id=row.id,
        review_gate_id=row.review_gate_id,
    )
