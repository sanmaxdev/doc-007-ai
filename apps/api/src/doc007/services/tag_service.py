"""Tag business logic. All reads/writes are scoped by workspace_id."""

from __future__ import annotations

import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.exceptions import NotFoundError, ValidationError
from doc007.db.models.tag import DocumentTag, Tag

_MAX_TAG_LEN = 60


def _normalize(name: str) -> str:
    cleaned = name.strip().lower()
    if not cleaned:
        raise ValidationError("Tag name cannot be empty.")
    if len(cleaned) > _MAX_TAG_LEN:
        raise ValidationError(f"Tag name cannot exceed {_MAX_TAG_LEN} characters.")
    return cleaned


async def list_tags(db: AsyncSession, workspace_id: uuid.UUID) -> list[Tag]:
    result = await db.execute(
        select(Tag).where(Tag.workspace_id == workspace_id).order_by(Tag.name.asc())
    )
    return list(result.scalars().all())


async def get_tag(
    db: AsyncSession, workspace_id: uuid.UUID, tag_id: uuid.UUID
) -> Tag | None:
    result = await db.execute(
        select(Tag).where(Tag.id == tag_id, Tag.workspace_id == workspace_id)
    )
    return result.scalar_one_or_none()


async def get_document_tags(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> list[Tag]:
    result = await db.execute(
        select(Tag)
        .join(DocumentTag, DocumentTag.tag_id == Tag.id)
        .where(DocumentTag.document_id == document_id, Tag.workspace_id == workspace_id)
        .order_by(Tag.name.asc())
    )
    return list(result.scalars().all())


async def _get_or_create_tag(
    db: AsyncSession, workspace_id: uuid.UUID, name: str
) -> Tag:
    result = await db.execute(
        select(Tag).where(Tag.workspace_id == workspace_id, Tag.name == name)
    )
    tag = result.scalar_one_or_none()
    if tag is None:
        tag = Tag(workspace_id=workspace_id, name=name)
        db.add(tag)
        await db.flush()
    return tag


async def add_tag(
    db: AsyncSession, *, workspace_id: uuid.UUID, document_id: uuid.UUID, name: str
) -> list[Tag]:
    tag = await _get_or_create_tag(db, workspace_id, _normalize(name))

    exists = await db.execute(
        select(DocumentTag).where(
            DocumentTag.document_id == document_id, DocumentTag.tag_id == tag.id
        )
    )
    if exists.scalar_one_or_none() is None:
        db.add(DocumentTag(document_id=document_id, tag_id=tag.id))
    await db.commit()
    return await get_document_tags(db, workspace_id, document_id)


async def remove_tag(
    db: AsyncSession, *, workspace_id: uuid.UUID, document_id: uuid.UUID, tag_id: uuid.UUID
) -> list[Tag]:
    tag = await get_tag(db, workspace_id, tag_id)
    if tag is None:
        raise NotFoundError("Tag not found.")
    await db.execute(
        delete(DocumentTag).where(
            DocumentTag.document_id == document_id, DocumentTag.tag_id == tag_id
        )
    )
    await db.commit()
    return await get_document_tags(db, workspace_id, document_id)
