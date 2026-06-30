"""FastAPI dependencies: current user, workspace membership, role gates."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Path, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core import token_blocklist
from doc007.core.config import settings
from doc007.core.exceptions import (
    ForbiddenError,
    NotFoundError,
    RateLimitedError,
    UnauthorizedError,
)
from doc007.core.security import decode_token
from doc007.db.base import get_db
from doc007.db.models.apikey import ApiKey
from doc007.db.models.user import User
from doc007.db.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from doc007.rag.vector_store import VectorStore
from doc007.services import apikey_service, auth_service, workspace_service
from doc007.storage.base import Storage

_bearer = HTTPBearer(auto_error=False)


async def get_access_payload(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict[str, Any]:
    """Decode and validate the bearer access token, rejecting revoked ones."""
    if credentials is None:
        raise UnauthorizedError("Not authenticated.")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise UnauthorizedError("Invalid or expired token.")
    if await token_blocklist.is_revoked(str(payload.get("jti", ""))):
        raise UnauthorizedError("Token has been revoked.")
    return payload


async def get_current_user(
    payload: dict[str, Any] = Depends(get_access_payload),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid token subject.") from None

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return user


async def enforce_auth_rate_limit(request: Request) -> None:
    """Per-IP rate limit for the auth endpoints, to slow credential stuffing."""
    from doc007.core.rate_limit import enforce

    ip = request.client.host if request.client else "unknown"
    allowed = await enforce(
        key=f"auth:{ip}",
        limit=settings.auth_rate_limit,
        window_seconds=settings.auth_rate_window_seconds,
    )
    if not allowed:
        raise RateLimitedError("Too many attempts. Please wait a moment and try again.")


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


# ---- Public API (API-key auth + rate limiting) ---------------------------


@dataclass
class ApiKeyContext:
    api_key: ApiKey
    workspace: Workspace


async def get_api_key_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyContext:
    if credentials is None:
        raise UnauthorizedError("Missing API key.")
    key = await apikey_service.authenticate(db, credentials.credentials)
    if key is None:
        raise UnauthorizedError("Invalid or revoked API key.")
    workspace = await workspace_service.get_workspace(db, key.workspace_id)
    if workspace is None:
        raise UnauthorizedError("Workspace not found.")
    return ApiKeyContext(api_key=key, workspace=workspace)


async def enforce_public_rate_limit(
    ctx: ApiKeyContext = Depends(get_api_key_context),
) -> ApiKeyContext:
    from doc007.core.rate_limit import enforce

    if not await enforce(key=str(ctx.api_key.id)):
        raise RateLimitedError("Rate limit exceeded. Please slow down and retry shortly.")
    return ctx


# ---- Injected infrastructure (overridable in tests) ----------------------


def get_storage_dep() -> Storage:
    from doc007.storage import get_storage

    return get_storage()


def get_vector_store_dep() -> VectorStore:
    from doc007.rag.vector_store import get_vector_store

    return get_vector_store()


def get_enqueue_ingestion() -> Callable[[uuid.UUID], None]:
    def _enqueue(document_id: uuid.UUID) -> None:
        from doc007.workers.tasks import process_document

        process_document.delay(str(document_id))

    return _enqueue


def get_embedder_dep():
    from doc007.providers.embeddings import get_embedding_provider

    return get_embedding_provider()


def get_llm_dep():
    from doc007.providers.llm import get_llm_provider

    return get_llm_provider()
