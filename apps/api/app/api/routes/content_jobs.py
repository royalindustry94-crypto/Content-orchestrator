"""Private Beta content job API — submit drafts into the Review Gate."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.audit import audit
from app.core.authorization import require_workspace_content_author
from app.core.config import get_settings
from app.core.security import AuthenticatedUser, get_current_user
from app.db.session import AsyncSessionLocal
from app.models.content_profile import WorkspaceContentProfile
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.content_desk import ContentJobCreate, ContentJobOut
from app.services import billing as billing_service
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

    Optional script_body: when omitted, Draft Desk generates a script from
    topic. The Human Review Gate is never skipped. When BILLING_ENABLED,
    an active/trialing Pro entitlement is required.
    """
    try:
        async with AsyncSessionLocal() as session:
            if get_settings().billing_enabled:
                await billing_service.require_entitlement_for_workspace(
                    session, workspace_id=workspace_id
                )
            profile = (
                await session.execute(
                    select(WorkspaceContentProfile).where(
                        WorkspaceContentProfile.workspace_id == workspace_id
                    )
                )
            ).scalar_one_or_none()
            result = await content_desk.create_content_job(
                session,
                workspace_id=workspace_id,
                actor_id=uuid.UUID(user.id),
                topic=payload.topic.strip(),
                business_name=payload.business_name or (profile.business_name if profile else None),
                offer=payload.offer or (profile.offer if profile else None),
                target_audience=payload.target_audience
                or (profile.target_audience if profile else None),
                brand_voice=payload.brand_voice or (profile.brand_voice if profile else None),
                content_goal=payload.content_goal or (profile.content_goal if profile else None),
                target_platform=payload.target_platform
                or (profile.target_platform if profile else None),
                script_body=payload.script_body or "",
                script_hook=payload.script_hook,
                script_cta=payload.script_cta,
                target_length_seconds=payload.target_length_seconds
                or (profile.default_length_seconds if profile else None),
                idempotency_key=payload.idempotency_key,
            )
            await session.commit()
    except billing_service.BillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=exc.message,
        ) from exc
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="content job conflicts with an existing idempotency key",
        ) from exc
    except content_desk.SpendBudgetExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
