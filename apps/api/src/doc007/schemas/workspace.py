"""Workspace request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from doc007.db.models.workspace import MemberStatus, WorkspaceRole


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None
    created_at: datetime
    # The requesting user's role in this workspace (populated by the service).
    role: WorkspaceRole | None = None


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    email: EmailStr
    full_name: str | None
    role: WorkspaceRole
    status: MemberStatus
    joined_at: datetime
