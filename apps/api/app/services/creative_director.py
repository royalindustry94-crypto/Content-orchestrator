"""Provider-neutral Human Creative Director orchestration.

This service prepares and approves generation instructions only. It never calls
a media provider, spends money, or grants publication approval.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.creative_director import (
    CreativeBriefVersion,
    CreativeProject,
    PromptPackDecision,
    PromptPackVersion,
)


class CreativeProjectNotFoundError(Exception):
    """The requested workspace-scoped creative project does not exist."""


class CreativeConflictError(Exception):
    """The requested mutation targets stale or inconsistent creative state."""


def _fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


async def get_project(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    for_update: bool = False,
) -> CreativeProject:
    query = select(CreativeProject).where(
        CreativeProject.workspace_id == workspace_id,
        CreativeProject.id == project_id,
    )
    if for_update:
        query = query.with_for_update()
    project = (await session.execute(query)).scalar_one_or_none()
    if project is None:
        raise CreativeProjectNotFoundError("creative project not found")
    return project


async def _latest_brief(
    session: AsyncSession, *, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> CreativeBriefVersion | None:
    return (
        await session.execute(
            select(CreativeBriefVersion)
            .where(
                CreativeBriefVersion.workspace_id == workspace_id,
                CreativeBriefVersion.project_id == project_id,
            )
            .order_by(CreativeBriefVersion.revision_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _latest_prompt_pack(
    session: AsyncSession, *, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> PromptPackVersion | None:
    return (
        await session.execute(
            select(PromptPackVersion)
            .where(
                PromptPackVersion.workspace_id == workspace_id,
                PromptPackVersion.project_id == project_id,
            )
            .order_by(PromptPackVersion.revision_number.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _latest_decision(
    session: AsyncSession, *, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> PromptPackDecision | None:
    return (
        await session.execute(
            select(PromptPackDecision)
            .where(
                PromptPackDecision.workspace_id == workspace_id,
                PromptPackDecision.project_id == project_id,
            )
            .order_by(PromptPackDecision.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()


def _brief_payload(
    *, customer_request: str, requirements: dict, exclusions: list[str], reference_notes: str | None
) -> dict:
    return {
        "customer_request": customer_request,
        "requirements": requirements,
        "exclusions": exclusions,
        "reference_notes": reference_notes,
    }


async def create_project(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID,
    title: str,
    desired_outcome: str,
    customer_request: str,
    requirements: dict,
    exclusions: list[str],
    reference_notes: str | None,
) -> tuple[CreativeProject, CreativeBriefVersion]:
    project = CreativeProject(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        title=title,
        desired_outcome=desired_outcome,
        status="brief_ready",
        created_by=actor_id,
        updated_by=actor_id,
    )
    session.add(project)
    await session.flush()

    payload = _brief_payload(
        customer_request=customer_request,
        requirements=requirements,
        exclusions=exclusions,
        reference_notes=reference_notes,
    )
    brief = CreativeBriefVersion(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        project_id=project.id,
        revision_number=1,
        fingerprint=_fingerprint(payload),
        created_by=actor_id,
        **payload,
    )
    session.add(brief)
    await session.flush()
    return project, brief


async def create_brief_version(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    customer_request: str,
    requirements: dict,
    exclusions: list[str],
    reference_notes: str | None,
) -> CreativeBriefVersion:
    project = await get_project(
        session, workspace_id=workspace_id, project_id=project_id, for_update=True
    )
    if project.status == "archived":
        raise CreativeConflictError("archived creative projects cannot be revised")
    revision = (
        await session.scalar(
            select(func.coalesce(func.max(CreativeBriefVersion.revision_number), 0)).where(
                CreativeBriefVersion.workspace_id == workspace_id,
                CreativeBriefVersion.project_id == project_id,
            )
        )
    ) + 1
    payload = _brief_payload(
        customer_request=customer_request,
        requirements=requirements,
        exclusions=exclusions,
        reference_notes=reference_notes,
    )
    brief = CreativeBriefVersion(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        project_id=project_id,
        revision_number=revision,
        fingerprint=_fingerprint(payload),
        created_by=actor_id,
        **payload,
    )
    session.add(brief)
    project.status = "brief_ready"
    project.updated_by = actor_id
    await session.flush()
    return brief


async def create_prompt_pack(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    actor_id: uuid.UUID,
    brief_version_id: uuid.UUID,
    target_tool: str | None,
    prompt_spec: dict,
    continuity_rules: list[str],
    negative_prompts: list[str],
    validation_checklist: list[str],
    estimated_generation_count: int,
) -> PromptPackVersion:
    project = await get_project(
        session, workspace_id=workspace_id, project_id=project_id, for_update=True
    )
    if project.status == "archived":
        raise CreativeConflictError("archived creative projects cannot be revised")
    latest_brief = await _latest_brief(
        session, workspace_id=workspace_id, project_id=project_id
    )
    if latest_brief is None or latest_brief.id != brief_version_id:
        raise CreativeConflictError("prompt pack must use the latest creative brief version")

    revision = (
        await session.scalar(
            select(func.coalesce(func.max(PromptPackVersion.revision_number), 0)).where(
                PromptPackVersion.workspace_id == workspace_id,
                PromptPackVersion.project_id == project_id,
            )
        )
    ) + 1
    payload = {
        "brief_fingerprint": latest_brief.fingerprint,
        "target_tool": target_tool,
        "prompt_spec": prompt_spec,
        "continuity_rules": continuity_rules,
        "negative_prompts": negative_prompts,
        "validation_checklist": validation_checklist,
        "estimated_generation_count": estimated_generation_count,
    }
    pack = PromptPackVersion(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        project_id=project_id,
        brief_version_id=brief_version_id,
        revision_number=revision,
        fingerprint=_fingerprint(payload),
        created_by=actor_id,
        target_tool=target_tool,
        prompt_spec=prompt_spec,
        continuity_rules=continuity_rules,
        negative_prompts=negative_prompts,
        validation_checklist=validation_checklist,
        estimated_generation_count=estimated_generation_count,
    )
    session.add(pack)
    project.status = "prompt_review"
    project.updated_by = actor_id
    await session.flush()
    return pack


async def decide_prompt_pack(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    project_id: uuid.UUID,
    prompt_pack_version_id: uuid.UUID,
    expected_fingerprint: str,
    reviewer_id: uuid.UUID,
    approved: bool,
    notes: str | None,
) -> PromptPackDecision:
    await get_project(
        session, workspace_id=workspace_id, project_id=project_id, for_update=True
    )
    latest_pack = await _latest_prompt_pack(
        session, workspace_id=workspace_id, project_id=project_id
    )
    if latest_pack is None or latest_pack.id != prompt_pack_version_id:
        raise CreativeConflictError("only the latest prompt pack can be decided")
    if not hmac.compare_digest(latest_pack.fingerprint, expected_fingerprint):
        raise CreativeConflictError("prompt pack fingerprint does not match the reviewed version")
    existing = (
        await session.execute(
            select(PromptPackDecision).where(
                PromptPackDecision.workspace_id == workspace_id,
                PromptPackDecision.prompt_pack_version_id == prompt_pack_version_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise CreativeConflictError("prompt pack already has a decision; create a new version")

    decision = PromptPackDecision(
        id=uuid.uuid4(),
        workspace_id=workspace_id,
        project_id=project_id,
        prompt_pack_version_id=prompt_pack_version_id,
        prompt_pack_fingerprint=latest_pack.fingerprint,
        decision="approved" if approved else "changes_requested",
        notes=notes,
        reviewer_id=reviewer_id,
    )
    session.add(decision)
    await session.flush()
    return decision


async def project_detail(
    session: AsyncSession, *, workspace_id: uuid.UUID, project_id: uuid.UUID
) -> dict:
    project = await get_project(session, workspace_id=workspace_id, project_id=project_id)
    brief = await _latest_brief(session, workspace_id=workspace_id, project_id=project_id)
    if brief is None:
        raise CreativeConflictError("creative project has no brief version")
    pack = await _latest_prompt_pack(session, workspace_id=workspace_id, project_id=project_id)
    decision = await _latest_decision(session, workspace_id=workspace_id, project_id=project_id)
    approved = bool(
        pack
        and decision
        and decision.prompt_pack_version_id == pack.id
        and decision.prompt_pack_fingerprint == pack.fingerprint
        and decision.decision == "approved"
    )
    return {
        "project": project,
        "latest_brief": brief,
        "latest_prompt_pack": pack,
        "latest_decision": decision,
        "approved_for_generation": approved,
    }


async def list_projects(
    session: AsyncSession, *, workspace_id: uuid.UUID
) -> list[CreativeProject]:
    return list(
        (
            await session.execute(
                select(CreativeProject)
                .where(CreativeProject.workspace_id == workspace_id)
                .order_by(CreativeProject.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
