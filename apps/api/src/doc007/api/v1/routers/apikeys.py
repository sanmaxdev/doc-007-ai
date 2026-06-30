"""API key management (workspace-scoped, admin+)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import require_role
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.audit import AuditAction
from doc007.db.models.workspace import WorkspaceMember, WorkspaceRole
from doc007.schemas.apikey import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from doc007.services import apikey_service, audit_service

router = APIRouter()

_ADMIN = require_role(WorkspaceRole.owner, WorkspaceRole.admin)


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: ApiKeyCreate,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreated:
    key, raw = await apikey_service.create_key(
        db, workspace_id=membership.workspace_id, name=data.name, created_by=membership.user_id
    )
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.apikey_created,
        target_type="api_key",
        target_id=key.id,
        details={"name": key.name},
    )
    return ApiKeyCreated(api_key=ApiKeyOut.model_validate(key), key=raw)


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> list[ApiKeyOut]:
    keys = await apikey_service.list_keys(db, membership.workspace_id)
    return [ApiKeyOut.model_validate(k) for k in keys]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    membership: WorkspaceMember = Depends(_ADMIN),
    db: AsyncSession = Depends(get_db),
) -> Response:
    key = await apikey_service.get_key(db, membership.workspace_id, key_id)
    if key is None:
        raise NotFoundError("API key not found.")
    await apikey_service.revoke_key(db, key)
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.apikey_revoked,
        target_type="api_key",
        target_id=key_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
