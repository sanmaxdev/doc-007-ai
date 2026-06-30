"""Invitation acceptance (not workspace-scoped — the caller isn't a member yet)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_current_user
from doc007.db.base import get_db
from doc007.db.models.audit import AuditAction
from doc007.db.models.user import User
from doc007.schemas.workspace import InvitationAccept, WorkspaceOut
from doc007.services import audit_service, workspace_service

router = APIRouter()


@router.post("/accept", response_model=WorkspaceOut)
async def accept_invitation(
    data: InvitationAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceOut:
    ws = await workspace_service.accept_invitation(
        db, token=data.token, user=current_user
    )
    await audit_service.record(
        db,
        workspace_id=ws.id,
        actor_id=current_user.id,
        action=AuditAction.invitation_accepted,
    )
    out = WorkspaceOut.model_validate(ws)
    membership = await workspace_service.get_membership(db, ws.id, current_user.id)
    out.role = membership.role if membership else None
    return out
