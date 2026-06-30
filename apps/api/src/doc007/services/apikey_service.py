"""API key business logic. Raw keys are shown once; only hashes are stored."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.core.security import generate_token, hash_token
from doc007.db.models.apikey import ApiKey


async def create_key(
    db: AsyncSession, *, workspace_id: uuid.UUID, name: str, created_by: uuid.UUID
) -> tuple[ApiKey, str]:
    raw = f"{settings.api_key_prefix}_{generate_token()}"
    key = ApiKey(
        workspace_id=workspace_id,
        name=name.strip() or "API key",
        key_prefix=raw[:12],
        hashed_key=hash_token(raw),
        created_by=created_by,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    return key, raw


async def list_keys(db: AsyncSession, workspace_id: uuid.UUID) -> list[ApiKey]:
    result = await db.execute(
        select(ApiKey)
        .where(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
    )
    return list(result.scalars().all())


async def get_key(
    db: AsyncSession, workspace_id: uuid.UUID, key_id: uuid.UUID
) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(ApiKey.id == key_id, ApiKey.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def revoke_key(db: AsyncSession, key: ApiKey) -> None:
    if key.revoked_at is None:
        key.revoked_at = datetime.now(UTC)
        await db.commit()


async def authenticate(db: AsyncSession, raw_key: str) -> ApiKey | None:
    result = await db.execute(
        select(ApiKey).where(
            ApiKey.hashed_key == hash_token(raw_key),
            ApiKey.revoked_at.is_(None),
        )
    )
    key = result.scalar_one_or_none()
    if key is not None:
        key.last_used_at = datetime.now(UTC)
        await db.commit()
    return key
