"""Retrieval: embed the query, search Qdrant (workspace-filtered), hydrate chunks."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.db.models.document import Document, DocumentChunk
from doc007.providers.base import EmbeddingProvider
from doc007.rag.vector_store import VectorStore


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_filename: str
    page_number: int | None
    content: str
    score: float


async def retrieve(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    query: str,
    embedder: EmbeddingProvider,
    vector_store: VectorStore,
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
) -> list[RetrievedChunk]:
    query_vector = (await embedder.embed([query]))[0]
    hits = await vector_store.search(
        workspace_id=workspace_id,
        vector=query_vector,
        top_k=top_k,
        document_ids=document_ids,
    )
    if not hits:
        return []

    chunk_ids = [uuid.UUID(h.chunk_id) for h in hits]
    # Re-scope to the workspace in SQL too (defense in depth).
    rows = await session.execute(
        select(DocumentChunk).where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.workspace_id == workspace_id,
        )
    )
    by_id = {row.id: row for row in rows.scalars()}

    doc_ids = {row.document_id for row in by_id.values()}
    names: dict[uuid.UUID, str] = {}
    if doc_ids:
        docs = await session.execute(select(Document).where(Document.id.in_(doc_ids)))
        names = {d.id: d.original_filename for d in docs.scalars()}

    retrieved: list[RetrievedChunk] = []
    for hit in hits:
        cid = uuid.UUID(hit.chunk_id)
        row = by_id.get(cid)
        if row is None:
            continue
        retrieved.append(
            RetrievedChunk(
                chunk_id=str(cid),
                document_id=str(row.document_id),
                document_filename=names.get(row.document_id, "document"),
                page_number=row.page_number,
                content=row.content,
                score=hit.score,
            )
        )
    return retrieved
