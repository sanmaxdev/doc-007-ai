"""Workspace endpoints: create, list, get, members."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_current_user, get_membership
from doc007.db.base import get_db
from doc007.db.models.user import User
from doc007.db.models.workspace import WorkspaceMember, WorkspaceRole
from doc007.schemas.workspace import MemberOut, WorkspaceCreate, WorkspaceOut
from doc007.services import workspace_service

router = APIRouter()


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    ws = await workspace_service.create_workspace(
        db, owner=current_user, name=data.name, description=data.description
    )
    out = WorkspaceOut.model_validate(ws)
    out.role = WorkspaceRole.owner  # the creator is always the owner
    return out


@router.get("", response_model=list[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[WorkspaceOut]:
    memberships = await workspace_service.list_memberships_for_user(db, current_user.id)
    result: list[WorkspaceOut] = []
    for m in memberships:
        out = WorkspaceOut.model_validate(m.workspace)
        out.role = m.role
        result.append(out)
    return result


@router.get("/{workspace_id}", response_model=WorkspaceOut)
async def get_workspace(
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    ws = await workspace_service.get_workspace(db, membership.workspace_id)
    out = WorkspaceOut.model_validate(ws)
    out.role = membership.role
    return out


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    members = await workspace_service.list_members(db, membership.workspace_id)
    return [
        MemberOut(
            user_id=m.user_id,
            email=m.user.email,
            full_name=m.user.full_name,
            role=m.role,
            status=m.status,
            joined_at=m.joined_at,
        )
        for m in members
    ]
