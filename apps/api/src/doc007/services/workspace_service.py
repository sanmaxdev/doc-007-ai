"""Workspace and membership business logic.

Tenant isolation starts here: callers only ever reach a workspace through
`get_membership`, which returns None when the user is not an active member.
"""

from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from doc007.db.models.user import User
from doc007.db.models.workspace import (
    MemberStatus,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

_slug_re = re.compile(r"[^a-z0-9]+")


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
    db: AsyncSession, workspace_id: uuid.UUID
) -> list[WorkspaceMember]:
    result = await db.execute(
        select(WorkspaceMember)
        .where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.status == MemberStatus.active,
        )
        .options(selectinload(WorkspaceMember.user))
        .order_by(WorkspaceMember.joined_at.asc())
    )
    return list(result.scalars().all())
