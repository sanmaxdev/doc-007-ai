"""Retrieval debug/eval endpoint (workspace-scoped). No LLM call."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.core.deps import get_embedder_dep, get_membership, get_vector_store_dep
from doc007.db.base import get_db
from doc007.db.models.workspace import WorkspaceMember
from doc007.providers.base import EmbeddingProvider
from doc007.rag.vector_store import VectorStore
from doc007.schemas.search import RetrievedChunkOut, RetrieveRequest, RetrieveResponse
from doc007.services import search_service

router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_debug(
    payload: RetrieveRequest,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder_dep),
    vector_store: VectorStore = Depends(get_vector_store_dep),
) -> RetrieveResponse:
    chunks, prompt, not_found, method = await search_service.debug_retrieve(
        db,
        workspace_id=membership.workspace_id,
        question=payload.question,
        embedder=embedder,
        vector_store=vector_store,
        top_k=payload.top_k or settings.retrieval_top_k,
        document_ids=payload.document_ids,
        hybrid=payload.hybrid,
    )
    return RetrieveResponse(
        question=payload.question,
        method=method,
        not_found=not_found,
        prompt=prompt,
        chunks=[
            RetrievedChunkOut(
                chunk_id=uuid.UUID(c.chunk_id),
                document_id=uuid.UUID(c.document_id),
                document_filename=c.document_filename,
                page_number=c.page_number,
                chunk_index=c.chunk_index,
                content=c.content,
                score=c.score,
                lexical_score=c.lexical_score,
                fused_score=c.fused_score,
                dense_rank=c.dense_rank,
                lexical_rank=c.lexical_rank,
            )
            for c in chunks
        ],
    )
