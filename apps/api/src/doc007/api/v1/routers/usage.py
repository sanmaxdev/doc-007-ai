"""Usage summary (workspace-scoped, any member)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_membership
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.workspace import WorkspaceMember
from doc007.schemas.usage import UsageSummaryOut
from doc007.services import usage_service, workspace_service

router = APIRouter()


@router.get("", response_model=UsageSummaryOut)
async def get_usage(
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> UsageSummaryOut:
    workspace = await workspace_service.get_workspace(db, membership.workspace_id)
    if workspace is None:
        raise NotFoundError("Workspace not found.")
    summary = await usage_service.usage_summary(db, workspace)
    return UsageSummaryOut(**summary)
