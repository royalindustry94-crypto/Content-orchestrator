"""Private Beta review desk API — list and decide Human Review Gates.

Uses the RLS-scoped runtime session (`Depends(get_current_session)`), like
every other tenant-scoped route, as of migration 0052 (2026-09-07 TD-072
fix). Previously used the owner DB connection because
`app.orchestration.controller` is shared with the connectionless
background scheduler, which has no per-request JWT context — that
scheduler path still uses the owner connection (unaffected by this route).
See `docs/TECHNICAL_DEBT_REGISTER.md` (TD-072) for the write-surface audit
that this migration closes, and `tests/test_content_desk_workspace_scoping.py`
and `tests/test_review_desk_api.py::test_cross_workspace_review_gate_is_hidden`
for the compensating isolation tests that predate and now double-check
this RLS backstop.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import (
    require_workspace_content_author,
    require_workspace_member,
    require_workspace_reviewer,
)
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.enums import ReviewGateStatus
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.content_desk import ReviewDecisionIn, ReviewGateEditIn, ReviewGateOut
from app.services import content_desk

router = APIRouter(prefix="/workspaces/{workspace_id}/review-gates", tags=["review-gates"])

_VALID_STATUSES = {s.value for s in ReviewGateStatus}


@router.get("", response_model=list[ReviewGateOut])
async def list_review_gates(
    workspace_id: uuid.UUID,
    status_filter: str | None = Query(default="awaiting", alias="status"),
    limit: int | None = Query(default=None, ge=1, le=200),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> list[ReviewGateOut]:
    if status_filter is not None and status_filter != "all":
        if status_filter not in _VALID_STATUSES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"status must be one of: {', '.join(sorted(_VALID_STATUSES))}, all",
            )
    filter_value = None if status_filter in (None, "all") else status_filter
    rows = await content_desk.list_review_gates(
        db, workspace_id=workspace_id, status_filter=filter_value, limit=limit
    )
    return [ReviewGateOut.model_validate(row) for row in rows]


@router.get("/{gate_id}", response_model=ReviewGateOut)
async def get_review_gate(
    workspace_id: uuid.UUID,
    gate_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> ReviewGateOut:
    row = await content_desk.get_review_gate(db, workspace_id=workspace_id, gate_id=gate_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="review gate not found")
    return ReviewGateOut.model_validate(row)


@router.patch("/{gate_id}", response_model=ReviewGateOut)
async def edit_review_gate(
    workspace_id: uuid.UUID,
    gate_id: uuid.UUID,
    payload: ReviewGateEditIn,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> ReviewGateOut:
    """Edit a gate's script content while it is still AWAITING a decision.

    Scoped to the same roles that may write content (`content_versions`/
    `content_items` RLS both require admin or editor) rather than the
    reviewer role used for decisions — reviewers approve/reject, editors
    (and admins, who can also decide) author and revise content.
    """
    try:
        row = await content_desk.edit_review_gate_content(
            db,
            workspace_id=workspace_id,
            gate_id=gate_id,
            editor_id=uuid.UUID(user.id),
            expected_content_version_id=payload.expected_content_version_id,
            script_hook=payload.script_hook,
            script_body=payload.script_body,
            script_cta=payload.script_cta,
        )
    except content_desk.ReviewGateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review gate not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    audit(
        request,
        "review_gate_content_edited",
        workspace_id=str(workspace_id),
        review_gate_id=str(gate_id),
        editor_id=user.id,
    )
    return ReviewGateOut.model_validate(row)


@router.post("/{gate_id}/decision", response_model=ReviewGateOut)
async def decide_review_gate(
    workspace_id: uuid.UUID,
    gate_id: uuid.UUID,
    payload: ReviewDecisionIn,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_reviewer),
) -> ReviewGateOut:
    """Approve or reject a gate. Editors cannot decide (matches review_decisions RLS)."""
    try:
        row = await content_desk.decide_review_gate(
            db,
            workspace_id=workspace_id,
            gate_id=gate_id,
            reviewer_id=uuid.UUID(user.id),
            approved=payload.approved,
            notes=payload.notes,
            expected_content_version_id=payload.expected_content_version_id,
        )
    except content_desk.ReviewGateNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="review gate not found"
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except content_desk.ReviewGateDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="review decision could not be applied; retry safely",
        ) from exc

    audit(
        request,
        "review_gate_decided",
        workspace_id=str(workspace_id),
        review_gate_id=str(gate_id),
        approved=payload.approved,
        reviewer_id=user.id,
    )
    return ReviewGateOut.model_validate(row)
