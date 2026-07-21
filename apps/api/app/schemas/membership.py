from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.workspace_membership import WorkspaceRole


class MembershipCreate(BaseModel):
    user_id: uuid.UUID
    role: WorkspaceRole


class MembershipRoleUpdate(BaseModel):
    role: WorkspaceRole


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    user_id: uuid.UUID
    role: WorkspaceRole
    created_at: datetime
