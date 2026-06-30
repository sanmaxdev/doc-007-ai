"""Document endpoints (workspace-scoped): upload, list, get, delete, reprocess, chunks, tags."""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import (
    get_enqueue_ingestion,
    get_membership,
    get_storage_dep,
    get_vector_store_dep,
)
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.audit import AuditAction
from doc007.db.models.document import DocumentStatus
from doc007.db.models.workspace import WorkspaceMember
from doc007.rag.vector_store import VectorStore
from doc007.schemas.document import ChunkOut, DocumentOut, TagCreate, TagOut
from doc007.services import audit_service, document_service, tag_service
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
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.document_upload,
        target_type="document",
        target_id=doc.id,
        details={"filename": doc.original_filename},
    )
    return DocumentOut.model_validate(doc)


@router.get("", response_model=list[DocumentOut])
async def list_documents(
    status_filter: DocumentStatus | None = None,
    search: str | None = Query(default=None, max_length=255),
    tag_id: uuid.UUID | None = None,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    docs = await document_service.list_documents(
        db, membership.workspace_id, status=status_filter, search=search, tag_id=tag_id
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
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.document_reprocess,
        target_type="document",
        target_id=doc.id,
    )
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
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.document_delete,
        target_type="document",
        target_id=document_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---- Tags ----------------------------------------------------------------


@router.post("/{document_id}/tags", response_model=list[TagOut])
async def add_document_tag(
    document_id: uuid.UUID,
    data: TagCreate,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[TagOut]:
    doc = await document_service.get_document(db, membership.workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    tags = await tag_service.add_tag(
        db, workspace_id=membership.workspace_id, document_id=document_id, name=data.name
    )
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.tag_added,
        target_type="document",
        target_id=document_id,
        details={"tag": data.name.strip().lower()},
    )
    return [TagOut.model_validate(t) for t in tags]


@router.delete("/{document_id}/tags/{tag_id}", response_model=list[TagOut])
async def remove_document_tag(
    document_id: uuid.UUID,
    tag_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[TagOut]:
    doc = await document_service.get_document(db, membership.workspace_id, document_id)
    if doc is None:
        raise NotFoundError("Document not found.")
    tags = await tag_service.remove_tag(
        db, workspace_id=membership.workspace_id, document_id=document_id, tag_id=tag_id
    )
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.tag_removed,
        target_type="document",
        target_id=document_id,
    )
    return [TagOut.model_validate(t) for t in tags]
