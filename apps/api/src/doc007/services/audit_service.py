"""Audit logging.

Append-only. `record` commits its own row so a failed audit write never
rolls back the action it describes, and vice versa. Call it after the action
it records has succeeded.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.db.models.audit import AuditAction, AuditLog


async def record(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    action: AuditAction,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AuditLog(
            workspace_id=workspace_id,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=details,
        )
    )
    await db.commit()


async def list_logs(
    db: AsyncSession, workspace_id: uuid.UUID, *, limit: int = 100, offset: int = 0
) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog)
        .where(AuditLog.workspace_id == workspace_id)
        .order_by(AuditLog.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
