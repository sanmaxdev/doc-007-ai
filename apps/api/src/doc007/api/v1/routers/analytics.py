"""Workspace analytics (read-only, any member)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_membership
from doc007.db.base import get_db
from doc007.db.models.workspace import WorkspaceMember
from doc007.schemas.analytics import AnalyticsOut
from doc007.services import analytics_service

router = APIRouter()


@router.get("", response_model=AnalyticsOut)
async def get_analytics(
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOut:
    data = await analytics_service.workspace_analytics(db, membership.workspace_id)
    return AnalyticsOut(**data)
