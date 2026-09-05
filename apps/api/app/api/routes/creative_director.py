"""Human Creative Director routes.

These endpoints prepare provider-neutral generation instructions. Approval here
authorizes a prompt pack for later generation; it never authorizes publication.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.authorization import (
    require_workspace_content_author,
    require_workspace_member,
    require_workspace_reviewer,
)
from app.core.security import AuthenticatedUser, get_current_session, get_current_user
from app.models.workspace_membership import WorkspaceMembership
from app.schemas.creative_director import (
    CreativeBriefInput,
    CreativeBriefOut,
    CreativeProjectCreate,
    CreativeProjectDetail,
    CreativeProjectOut,
    PromptPackDecisionInput,
    PromptPackDecisionOut,
    PromptPackInput,
    PromptPackOut,
)
from app.services import creative_director

router = APIRouter(
    prefix="/workspaces/{workspace_id}/creative-director",
    tags=["human-creative-director"],
)


def _not_found(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


def _conflict(exc: Exception) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post(
    "/projects", response_model=CreativeProjectDetail, status_code=status.HTTP_201_CREATED
)
async def create_project(
    workspace_id: uuid.UUID,
    payload: CreativeProjectCreate,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> CreativeProjectDetail:
    project, _brief = await creative_director.create_project(
        db,
        workspace_id=workspace_id,
        actor_id=uuid.UUID(user.id),
        title=payload.title,
        desired_outcome=payload.desired_outcome,
        **payload.brief.model_dump(),
    )
    detail = await creative_director.project_detail(
        db, workspace_id=workspace_id, project_id=project.id
    )
    audit(
        request,
        "creative_project_created",
        workspace_id=str(workspace_id),
        project_id=str(project.id),
        actor_user_id=user.id,
    )
    return CreativeProjectDetail(**detail)


@router.get("/projects", response_model=list[CreativeProjectOut])
async def projects(
    workspace_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> list[CreativeProjectOut]:
    rows = await creative_director.list_projects(db, workspace_id=workspace_id)
    return [CreativeProjectOut.model_validate(row) for row in rows]


@router.get("/projects/{project_id}", response_model=CreativeProjectDetail)
async def project_detail(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_member()),
) -> CreativeProjectDetail:
    try:
        detail = await creative_director.project_detail(
            db, workspace_id=workspace_id, project_id=project_id
        )
    except creative_director.CreativeProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except creative_director.CreativeConflictError as exc:
        raise _conflict(exc) from exc
    return CreativeProjectDetail(**detail)


@router.post(
    "/projects/{project_id}/brief-versions",
    response_model=CreativeBriefOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_brief_version(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: CreativeBriefInput,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> CreativeBriefOut:
    try:
        brief = await creative_director.create_brief_version(
            db,
            workspace_id=workspace_id,
            project_id=project_id,
            actor_id=uuid.UUID(user.id),
            **payload.model_dump(),
        )
    except creative_director.CreativeProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except creative_director.CreativeConflictError as exc:
        raise _conflict(exc) from exc
    audit(
        request,
        "creative_brief_version_created",
        workspace_id=str(workspace_id),
        project_id=str(project_id),
        brief_version_id=str(brief.id),
        revision_number=brief.revision_number,
        actor_user_id=user.id,
    )
    return CreativeBriefOut.model_validate(brief)


@router.post(
    "/projects/{project_id}/prompt-packs",
    response_model=PromptPackOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_prompt_pack(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    payload: PromptPackInput,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_content_author),
) -> PromptPackOut:
    try:
        pack = await creative_director.create_prompt_pack(
            db,
            workspace_id=workspace_id,
            project_id=project_id,
            actor_id=uuid.UUID(user.id),
            **payload.model_dump(),
        )
    except creative_director.CreativeProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except creative_director.CreativeConflictError as exc:
        raise _conflict(exc) from exc
    audit(
        request,
        "prompt_pack_version_created",
        workspace_id=str(workspace_id),
        project_id=str(project_id),
        prompt_pack_version_id=str(pack.id),
        revision_number=pack.revision_number,
        actor_user_id=user.id,
    )
    return PromptPackOut.model_validate(pack)


@router.post(
    "/projects/{project_id}/prompt-packs/{prompt_pack_version_id}/decision",
    response_model=PromptPackDecisionOut,
    status_code=status.HTTP_201_CREATED,
)
async def decide_prompt_pack(
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    prompt_pack_version_id: uuid.UUID,
    payload: PromptPackDecisionInput,
    request: Request,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_current_session),
    _membership: WorkspaceMembership = Depends(require_workspace_reviewer),
) -> PromptPackDecisionOut:
    try:
        decision = await creative_director.decide_prompt_pack(
            db,
            workspace_id=workspace_id,
            project_id=project_id,
            prompt_pack_version_id=prompt_pack_version_id,
            expected_fingerprint=payload.prompt_pack_fingerprint,
            reviewer_id=uuid.UUID(user.id),
            approved=payload.approved,
            notes=payload.notes,
        )
    except creative_director.CreativeProjectNotFoundError as exc:
        raise _not_found(exc) from exc
    except creative_director.CreativeConflictError as exc:
        raise _conflict(exc) from exc
    audit(
        request,
        "prompt_pack_decided",
        workspace_id=str(workspace_id),
        project_id=str(project_id),
        prompt_pack_version_id=str(prompt_pack_version_id),
        prompt_pack_fingerprint=decision.prompt_pack_fingerprint,
        decision=decision.decision,
        reviewer_user_id=user.id,
    )
    return PromptPackDecisionOut.model_validate(decision)
