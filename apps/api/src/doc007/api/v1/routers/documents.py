"""Document endpoints (workspace-scoped): upload, list, get, delete, reprocess, chunks."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import (
    get_enqueue_ingestion,
    get_membership,
    get_storage_dep,
    get_vector_store_dep,
)
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.document import DocumentStatus
from doc007.db.models.workspace import WorkspaceMember
from doc007.rag.vector_store import VectorStore
from doc007.schemas.document import ChunkOut, DocumentOut
from doc007.services import document_service
from doc007.storage.base import Storage

router = APIRouter()


@router.post("", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage_dep),
    enqueue: Callable[[uuid.UUID], None] = Depends(get_enqueue_ingestion),
) -> DocumentOut:
    data = await file.read()
    doc = await document_service.create_document(
        db,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        storage=storage,
    )
    enqueue(doc.id)
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    status_filter: DocumentStatus | None = None,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    docs = await document_service.list_documents(
        db, membership.workspace_id, status=status_filter
    )
    return [DocumentOut.model_validate(d) for d in docs]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    doc = await document_service.get_document(db, membership.workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    return DocumentOut.model_validate(doc)


@router.post("/{document_id}/reprocess", response_model=DocumentOut)
async def reprocess_document(
    document_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    enqueue: Callable[[uuid.UUID], None] = Depends(get_enqueue_ingestion),
) -> DocumentOut:
    doc = await document_service.get_document(db, membership.workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    await document_service.reset_for_reprocess(db, doc)
    enqueue(doc.id)
    return DocumentOut.model_validate(doc)


@router.get("/{document_id}/chunks", response_model=list[ChunkOut])
async def get_document_chunks(
    document_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ChunkOut]:
    doc = await document_service.get_document(db, membership.workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    chunks = await document_service.list_chunks(db, membership.workspace_id, document_id)
    return [ChunkOut.model_validate(c) for c in chunks]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage_dep),
    vector_store: VectorStore = Depends(get_vector_store_dep),
) -> Response:
    deleted = await document_service.delete_document(
        db,
        membership.workspace_id,
        document_id,
        storage=storage,
        vector_store=vector_store,
    )
    if not deleted:
        raise NotFoundError("Document not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
