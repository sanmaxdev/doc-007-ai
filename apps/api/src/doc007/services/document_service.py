"""Document business logic: validation, storage, CRUD, reprocess.

All reads are scoped by workspace_id (defense in depth on top of the
membership check in the router).
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.core.exceptions import ValidationError
from doc007.db.models.document import Document, DocumentChunk, DocumentStatus
from doc007.db.models.tag import DocumentTag
from doc007.rag.vector_store import VectorStore
from doc007.storage.base import Storage

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".markdown", ".docx"}


def _extension(filename: str) -> str:
    _, ext = os.path.splitext(filename.lower())
    return ext


def validate_upload(filename: str, size: int) -> None:
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise ValidationError(
            f"Unsupported file type '{ext or 'unknown'}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
        )
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if size == 0:
        raise ValidationError("Uploaded file is empty.")
    if size > max_bytes:
        raise ValidationError(f"File exceeds the {settings.max_upload_mb} MB limit.")


async def create_document(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    original_filename: str,
    content_type: str,
    data: bytes,
    storage: Storage,
) -> Document:
    validate_upload(original_filename, len(data))

    ext = _extension(original_filename)
    checksum = hashlib.sha256(data).hexdigest()
    storage_key = f"{workspace_id}/{uuid.uuid4().hex}{ext}"
    storage.save(storage_key, data)

    doc = Document(
        workspace_id=workspace_id,
        uploaded_by=user_id,
        filename=os.path.basename(storage_key),
        original_filename=original_filename,
        storage_key=storage_key,
        mime_type=content_type,
        file_size_bytes=len(data),
        checksum_sha256=checksum,
        status=DocumentStatus.uploaded,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


async def list_documents(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    *,
    status: DocumentStatus | None = None,
    search: str | None = None,
    tag_id: uuid.UUID | None = None,
) -> list[Document]:
    stmt = select(Document).where(Document.workspace_id == workspace_id)
    if status is not None:
        stmt = stmt.where(Document.status == status)
    if search:
        stmt = stmt.where(Document.original_filename.ilike(f"%{search.strip()}%"))
    if tag_id is not None:
        stmt = stmt.join(DocumentTag, DocumentTag.document_id == Document.id).where(
            DocumentTag.tag_id == tag_id
        )
    stmt = stmt.order_by(Document.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_document(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> Document | None:
    result = await db.execute(
        select(Document).where(
            Document.id == document_id, Document.workspace_id == workspace_id
        )
    )
    return result.scalar_one_or_none()


async def list_chunks(
    db: AsyncSession, workspace_id: uuid.UUID, document_id: uuid.UUID
) -> list[DocumentChunk]:
    result = await db.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.workspace_id == workspace_id,
        )
        .order_by(DocumentChunk.chunk_index.asc())
    )
    return list(result.scalars().all())


async def reset_for_reprocess(db: AsyncSession, doc: Document) -> None:
    doc.status = DocumentStatus.uploaded
    doc.error_message = None
    doc.chunk_count = 0
    doc.processed_at = None
    await db.commit()


async def delete_document(
    db: AsyncSession,
    workspace_id: uuid.UUID,
    document_id: uuid.UUID,
    *,
    storage: Storage,
    vector_store: VectorStore,
) -> bool:
    doc = await get_document(db, workspace_id, document_id)
    if doc is None:
        return False

    await vector_store.delete_document(workspace_id, document_id)
    with contextlib.suppress(FileNotFoundError):
        storage.delete(doc.storage_key)
    await db.delete(doc)
    await db.commit()
    return True
