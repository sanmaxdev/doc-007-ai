"""Public API (v1) — authenticated by API key, rate-limited per key.

Mounted at /api/public/v1 (separate from the JWT app API). Every endpoint
acts within the API key's workspace.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import (
    ApiKeyContext,
    enforce_public_rate_limit,
    get_embedder_dep,
    get_enqueue_ingestion,
    get_llm_dep,
    get_storage_dep,
    get_vector_store_dep,
)
from doc007.db.base import get_db
from doc007.providers.base import EmbeddingProvider, LLMProvider
from doc007.rag.vector_store import VectorStore
from doc007.schemas.chat import AskRequest, AskResponse, CitationOut
from doc007.schemas.document import DocumentOut
from doc007.services import chat_service, document_service
from doc007.storage.base import Storage

router = APIRouter()


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(
    ctx: ApiKeyContext = Depends(enforce_public_rate_limit),
    db: AsyncSession = Depends(get_db),
) -> list[DocumentOut]:
    docs = await document_service.list_documents(db, ctx.workspace.id)
    return [DocumentOut.model_validate(d) for d in docs]


@router.post("/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    ctx: ApiKeyContext = Depends(enforce_public_rate_limit),
    db: AsyncSession = Depends(get_db),
    storage: Storage = Depends(get_storage_dep),
    enqueue: Callable[[uuid.UUID], None] = Depends(get_enqueue_ingestion),
) -> DocumentOut:
    data = await file.read()
    doc = await document_service.create_document(
        db,
        workspace_id=ctx.workspace.id,
        user_id=ctx.api_key.created_by,
        original_filename=file.filename or "upload",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        storage=storage,
    )
    enqueue(doc.id)
    return DocumentOut.model_validate(doc)


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    ctx: ApiKeyContext = Depends(enforce_public_rate_limit),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder_dep),
    llm: LLMProvider = Depends(get_llm_dep),
    vector_store: VectorStore = Depends(get_vector_store_dep),
) -> AskResponse:
    user_id = ctx.api_key.created_by or ctx.workspace.owner_id
    conv, message, result = await chat_service.ask(
        db,
        workspace_id=ctx.workspace.id,
        user_id=user_id,
        question=payload.question,
        conversation_id=payload.conversation_id,
        document_ids=payload.document_ids,
        embedder=embedder,
        llm=llm,
        vector_store=vector_store,
        source="api",
    )
    return AskResponse(
        conversation_id=conv.id,
        message_id=message.id,
        answer=result.answer,
        citations=[
            CitationOut(
                index=c.index,
                document_id=uuid.UUID(c.document_id),
                document_filename=c.document_filename,
                page_number=c.page_number,
                snippet=c.snippet,
                score=c.score,
            )
            for c in result.citations
        ],
        coverage=result.coverage,
        not_found=result.not_found,
    )
