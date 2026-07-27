"""Private Beta content job API — submit drafts into the Review Gate."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError

from app.core.audit import audit
from app.core.authorization import require_workspace_content_author
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import AsyncSessionLocal
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.content_desk import ContentJobCreate, ContentJobOut
from app.services import content_desk

router = APIRouter(prefix="/workspaces/{workspace_id}/content-jobs", tags=["content-jobs"])


@router.post("", response_model=ContentJobOut, status_code=status.HTTP_201_CREATED)
async def create_content_job(
    workspace_id: uuid.UUID,
    payload: ContentJobCreate,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> ContentJobOut:
    """Create a content draft and place it in the mandatory Human Review Gate.

    Generation for Private Beta is the supplied script (stub). The Gate is
    never skipped. Orchestration writes use the service-role session after
    the role guard — pipeline/gate tables are not freely writable under RLS.
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await content_desk.create_content_job(
                session,
                workspace_id=workspace_id,
                actor_id=uuid.UUID(user.id),
                topic=payload.topic.strip(),
                script_body=payload.script_body,
                script_hook=payload.script_hook,
                script_cta=payload.script_cta,
                target_length_seconds=payload.target_length_seconds,
                idempotency_key=payload.idempotency_key,
            )
            await session.commit()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="content job conflicts with an existing idempotency key",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    audit(
        request,
        "content_job_created",
        workspace_id=str(workspace_id),
        content_item_id=str(result.content_item_id),
        pipeline_run_id=str(result.pipeline_run_id),
        review_gate_id=str(result.review_gate_id),
    )
    return ContentJobOut(
        content_item_id=result.content_item_id,
        pipeline_run_id=result.pipeline_run_id,
        review_gate_id=result.review_gate_id,
        topic=result.topic,
        current_stage=result.current_stage,
        run_status=result.run_status,
        gate_status=result.gate_status,
    )
