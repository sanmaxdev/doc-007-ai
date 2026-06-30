"""Workspace and membership business logic.

Tenant isolation starts here: callers only ever reach a workspace through
`get_membership`, which returns None when the user is not an active member.
"""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from doc007.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from doc007.core.security import generate_token, hash_token
from doc007.db.models.invitation import Invitation, InvitationStatus
from doc007.db.models.user import User
from doc007.db.models.workspace import (
    MemberStatus,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

_slug_re = re.compile(r"[^a-z0-9]+")
_INVITE_TTL_DAYS = 7


def slugify(name: str) -> str:
    base = _slug_re.sub("-", name.strip().lower()).strip("-")
    return base or "workspace"


async def create_workspace(
    db: AsyncSession, *, owner: User, name: str, description: str | None = None
) -> Workspace:
    slug = f"{slugify(name)}-{uuid.uuid4().hex[:6]}"
    workspace = Workspace(
        name=name.strip(),
        slug=slug,
        description=description,
        owner_id=owner.id,
    )
    workspace.members.append(
        WorkspaceMember(
            user_id=owner.id,
            role=WorkspaceRole.owner,
            status=MemberStatus.active,
        )
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def get_workspace(db: AsyncSession, workspace_id: uuid.UUID) -> Workspace | None:
    return await db.get(Workspace, workspace_id)


async def get_membership(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == MemberStatus.active,
        )
    )
    return result.scalar_one_or_none()


async def list_memberships_for_user(
    db: AsyncSession, user_id: uuid.UUID
) -> list[WorkspaceMember]:
    result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.user_id == user_id,
            WorkspaceMember.status == MemberStatus.active,
        )
        .options(selectinload(WorkspaceMember.workspace))
        .order_by(WorkspaceMember.created_at.asc())
    )
    return list(result.scalars().all())


async def list_members(
    db: AsyncSession, workspace_id: uuid.UUID, *, limit: int = 100, offset: int = 0
) -> list[WorkspaceMember]:
    result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == MemberStatus.active,
        )
        .options(selectinload(WorkspaceMember.user))
        .order_by(WorkspaceMember.joined_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


# ---- Workspace settings --------------------------------------------------


_UNSET: object = object()


async def update_workspace(
    db: AsyncSession,
    workspace: Workspace,
    *,
    name: str | None = None,
    description: str | None = None,
    monthly_question_limit: object = _UNSET,
) -> Workspace:
    if name is not None:
        workspace.name = name.strip()
    if description is not None:
        workspace.description = description.strip() or None
    if monthly_question_limit is not _UNSET:
        # Pass-through; None means "unlimited".
        workspace.monthly_question_limit = monthly_question_limit  # type: ignore[assignment]
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def delete_workspace(db: AsyncSession, workspace: Workspace) -> None:
    await db.delete(workspace)
    await db.commit()


# ---- Member management ---------------------------------------------------


async def get_member(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> WorkspaceMember | None:
    return await get_membership(db, workspace_id, user_id)


async def change_member_role(
    db: AsyncSession,
    *,
    workspace: Workspace,
    target_user_id: uuid.UUID,
    new_role: WorkspaceRole,
) -> WorkspaceMember:
    if new_role == WorkspaceRole.owner:
        raise ValidationError("Ownership transfer is not supported.")
    if target_user_id == workspace.owner_id:
        raise ForbiddenError("The workspace owner's role cannot be changed.")

    member = await get_member(db, workspace.id, target_user_id)
    if member is None:
        raise NotFoundError("Member not found.")

    member.role = new_role
    await db.commit()
    await db.refresh(member)
    return member


async def remove_member(
    db: AsyncSession,
    *,
    workspace: Workspace,
    actor_role: WorkspaceRole,
    target_user_id: uuid.UUID,
) -> None:
    if target_user_id == workspace.owner_id:
        raise ForbiddenError("The workspace owner cannot be removed.")

    member = await get_member(db, workspace.id, target_user_id)
    if member is None:
        raise NotFoundError("Member not found.")

    # Only an owner may remove an admin.
    if member.role == WorkspaceRole.admin and actor_role != WorkspaceRole.owner:
        raise ForbiddenError("Only the owner can remove an admin.")

    await db.delete(member)
    await db.commit()


# ---- Invitations ---------------------------------------------------------


async def create_invitation(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    email: str,
    role: WorkspaceRole,
    invited_by: uuid.UUID,
) -> tuple[Invitation, str]:
    if role == WorkspaceRole.owner:
        raise ValidationError("Cannot invite a user as owner.")

    email = email.strip().lower()

    # If the email already belongs to an active member, reject.
    existing = await db.execute(
        select(WorkspaceMember)
        .join(User, User.id == WorkspaceMember.user_id)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == MemberStatus.active,
            User.email == email,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise ConflictError("That person is already a member of this workspace.")

    # Supersede any outstanding pending invitations for the same email.
    pending = await db.execute(
        select(Invitation).where(
            Invitation.workspace_id == workspace_id,
            Invitation.email == email,
            Invitation.status == InvitationStatus.pending,
        )
    )
    for inv in pending.scalars().all():
        inv.status = InvitationStatus.revoked

    raw_token = generate_token()
    invitation = Invitation(
        workspace_id=workspace_id,
        email=email,
        role=role,
        token_hash=hash_token(raw_token),
        invited_by=invited_by,
        expires_at=datetime.now(UTC) + timedelta(days=_INVITE_TTL_DAYS),
    )
    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)
    return invitation, raw_token


async def list_invitations(
    db: AsyncSession, workspace_id: uuid.UUID, *, limit: int = 100, offset: int = 0
) -> list[Invitation]:
    result = await db.execute(
        select(Invitation)
        .where(
            Invitation.workspace_id == workspace_id,
            Invitation.status == InvitationStatus.pending,
        )
        .order_by(Invitation.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


async def get_invitation(
    db: AsyncSession, workspace_id: uuid.UUID, invitation_id: uuid.UUID
) -> Invitation | None:
    result = await db.execute(
        select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.workspace_id == workspace_id,
        )
    )
    return result.scalar_one_or_none()


async def revoke_invitation(db: AsyncSession, invitation: Invitation) -> None:
    invitation.status = InvitationStatus.revoked
    await db.commit()


async def accept_invitation(
    db: AsyncSession, *, token: str, user: User
) -> Workspace:
    result = await db.execute(
        select(Invitation).where(Invitation.token_hash == hash_token(token))
    )
    invitation = result.scalar_one_or_none()
    if invitation is None:
        raise NotFoundError("Invalid invitation.")
    if invitation.status != InvitationStatus.pending:
        raise ValidationError("This invitation is no longer valid.")

    expires_at = invitation.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at is not None and expires_at < datetime.now(UTC):
        invitation.status = InvitationStatus.expired
        await db.commit()
        raise ValidationError("This invitation has expired.")

    if invitation.email.lower() != user.email.lower():
        raise ForbiddenError("This invitation was sent to a different email address.")

    workspace = await get_workspace(db, invitation.workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")

    member = await get_member(db, invitation.workspace_id, user.id)
    if member is None:
        db.add(
            WorkspaceMember(
                workspace_id=invitation.workspace_id,
                user_id=user.id,
                role=invitation.role,
                status=MemberStatus.active,
                invited_by=invitation.invited_by,
            )
        )

    invitation.status = InvitationStatus.accepted
    await db.commit()
    return workspace
