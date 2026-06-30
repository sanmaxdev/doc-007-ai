"""Workspace endpoints: settings, members, invitations, audit logs."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_current_user, get_membership, require_role
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.audit import AuditAction
from doc007.db.models.user import User
from doc007.db.models.workspace import WorkspaceMember, WorkspaceRole
from doc007.schemas.document import TagOut
from doc007.schemas.workspace import (
    AuditLogOut,
    InvitationCreated,
    InvitationOut,
    InviteCreate,
    MemberOut,
    MemberRoleUpdate,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceUpdate,
)
from doc007.services import audit_service, tag_service, workspace_service

router = APIRouter()

_ADMIN = require_role(WorkspaceRole.owner, WorkspaceRole.admin)
_OWNER = require_role(WorkspaceRole.owner)


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
    out.role = WorkspaceRole.owner
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


@router.patch("/{workspace_id}", response_model=WorkspaceOut)
async def update_workspace(
    data: WorkspaceUpdate,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    ws = await workspace_service.get_workspace(db, membership.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found.")
    # Only apply fields the client actually sent (PATCH semantics).
    fields = data.model_fields_set
    kwargs: dict = {}
    if "name" in fields:
        kwargs["name"] = data.name
    if "description" in fields:
        kwargs["description"] = data.description
    if "monthly_question_limit" in fields:
        kwargs["monthly_question_limit"] = data.monthly_question_limit
    ws = await workspace_service.update_workspace(db, ws, **kwargs)
    await audit_service.record(
        db,
        workspace_id=ws.id,
        actor_id=membership.user_id,
        action=AuditAction.workspace_updated,
    )
    out = WorkspaceOut.model_validate(ws)
    out.role = membership.role
    return out


@router.delete("/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workspace(
    membership: WorkspaceMember = Depends(_OWNER),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ws = await workspace_service.get_workspace(db, membership.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found.")
    await workspace_service.delete_workspace(db, ws)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Tags ----------------------------------------------------------------


@router.get("/{workspace_id}/tags", response_model=list[TagOut])
async def list_tags(
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[TagOut]:
    tags = await tag_service.list_tags(db, membership.workspace_id, limit=limit, offset=offset)
    return [TagOut.model_validate(t) for t in tags]


# ---- Members -------------------------------------------------------------


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
async def list_members(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[MemberOut]:
    members = await workspace_service.list_members(
        db, membership.workspace_id, limit=limit, offset=offset
    )
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


@router.patch("/{workspace_id}/members/{user_id}/role", response_model=MemberOut)
async def change_member_role(
    user_id: uuid.UUID,
    data: MemberRoleUpdate,
    membership: WorkspaceMember = Depends(_OWNER),
    db: AsyncSession = Depends(get_db),
) -> MemberOut:
    ws = await workspace_service.get_workspace(db, membership.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found.")
    member = await workspace_service.change_member_role(
        db, workspace=ws, target_user_id=user_id, new_role=data.role
    )
    await db.refresh(member, attribute_names=["user"])
    await audit_service.record(
        db,
        workspace_id=ws.id,
        actor_id=membership.user_id,
        action=AuditAction.role_changed,
        target_type="user",
        target_id=user_id,
        details={"role": str(data.role)},
    )
    return MemberOut(
        user_id=member.user_id,
        email=member.user.email,
        full_name=member.user.full_name,
        role=member.role,
        status=member.status,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    user_id: uuid.UUID,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> Response:
    ws = await workspace_service.get_workspace(db, membership.workspace_id)
    if ws is None:
        raise NotFoundError("Workspace not found.")
    await workspace_service.remove_member(
        db, workspace=ws, actor_role=membership.role, target_user_id=user_id
    )
    await audit_service.record(
        db,
        workspace_id=ws.id,
        actor_id=membership.user_id,
        action=AuditAction.member_removed,
        target_type="user",
        target_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Invitations ---------------------------------------------------------


@router.post(
    "/{workspace_id}/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    data: InviteCreate,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> InvitationCreated:
    invitation, token = await workspace_service.create_invitation(
        db,
        workspace_id=membership.workspace_id,
        email=data.email,
        role=data.role,
        invited_by=membership.user_id,
    )
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.member_invited,
        target_type="invitation",
        target_id=invitation.id,
        details={"email": invitation.email, "role": str(invitation.role)},
    )
    return InvitationCreated(
        invitation=InvitationOut.model_validate(invitation), token=token
    )


@router.get("/{workspace_id}/invitations", response_model=list[InvitationOut])
async def list_invitations(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> list[InvitationOut]:
    invitations = await workspace_service.list_invitations(
        db, membership.workspace_id, limit=limit, offset=offset
    )
    return [InvitationOut.model_validate(i) for i in invitations]


@router.delete(
    "/{workspace_id}/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_invitation(
    invitation_id: uuid.UUID,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> Response:
    invitation = await workspace_service.get_invitation(
        db, membership.workspace_id, invitation_id
    )
    if invitation is None:
        raise NotFoundError("Invitation not found.")
    await workspace_service.revoke_invitation(db, invitation)
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.invitation_revoked,
        target_type="invitation",
        target_id=invitation_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Audit logs ----------------------------------------------------------


@router.get("/{workspace_id}/audit-logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLogOut]:
    logs = await audit_service.list_logs(
        db, membership.workspace_id, limit=limit, offset=offset
    )
    actor_ids = {log.actor_id for log in logs if log.actor_id is not None}
    emails: dict[uuid.UUID, str] = {}
    if actor_ids:
        rows = await db.execute(select(User.id, User.email).where(User.id.in_(actor_ids)))
        emails = {row.id: row.email for row in rows}
    return [
        AuditLogOut(
            id=log.id,
            action=str(log.action),
            actor_id=log.actor_id,
            actor_email=emails.get(log.actor_id) if log.actor_id else None,
            target_type=log.target_type,
            target_id=log.target_id,
            details=log.details,
            created_at=log.created_at,
        )
        for log in logs
    ]
