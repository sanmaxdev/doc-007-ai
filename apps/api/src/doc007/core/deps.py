"""FastAPI dependencies: current user, workspace membership, role gates."""

from __future__ import annotations

import uuid

from fastapi import Depends, Path
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from doc007.core.security import decode_token
from doc007.db.base import get_db
from doc007.db.models.user import User
from doc007.db.models.workspace import WorkspaceMember, WorkspaceRole
from doc007.services import auth_service, workspace_service

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token.")

    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid token subject.") from None

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


async def get_membership(
    workspace_id: uuid.UUID = Path(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMember:
    """Resolve the caller's membership in the path workspace.

    Returns 404 (not 403) when the user is not a member, so workspace
    existence is not leaked across tenants.
    """
    membership = await workspace_service.get_membership(db, workspace_id, current_user.id)
    if membership is None:
        raise NotFoundError("Workspace not found.")
    return membership


def require_role(*roles: WorkspaceRole):
    """Dependency factory: require the caller to hold one of `roles`."""

    async def _checker(
        membership: WorkspaceMember = Depends(get_membership),
    ) -> WorkspaceMember:
        if membership.role not in roles:
            raise ForbiddenError("You do not have permission to perform this action.")
        return membership

    return _checker
