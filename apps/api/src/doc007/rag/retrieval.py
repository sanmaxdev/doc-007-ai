"""Retrieval: dense (vector) + lexical (keyword), fused with Reciprocal Rank Fusion.

Dense recall comes from Qdrant (semantic). Lexical recall is a keyword scan over
chunk text in the DB (catches exact terms, IDs, names a dense model may miss).
The two ranked lists are merged with RRF. Every path is workspace-filtered.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.db.models.document import Document, DocumentChunk
from doc007.providers.base import EmbeddingProvider
from doc007.rag.vector_store import VectorStore

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "is", "are", "was", "were",
    "be", "for", "on", "at", "by", "with", "what", "how", "why", "when", "where",
    "who", "which", "does", "do", "did", "this", "that", "it", "as", "from", "can",
    "could", "should", "would", "our", "we", "you", "your", "they", "their", "about",
}


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    document_filename: str
    page_number: int | None
    content: str
    score: float  # dense cosine similarity (0.0 if found only via lexical search)
    chunk_index: int = 0
    lexical_score: float = 0.0
    fused_score: float = 0.0
    dense_rank: int | None = None
    lexical_rank: int | None = None
    method: str = "vector"


def _terms(query: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", query.lower())
    return [t for t in tokens if len(t) >= 3 and t not in _STOPWORDS]


def passes_guardrail(chunks: list[RetrievedChunk]) -> bool:
    """True if the retrieved set is relevant enough to answer from.

    Semantic match (dense >= threshold) OR a literal keyword match. Otherwise
    we refuse rather than let the LLM hallucinate.
    """
    if not chunks:
        return False
    best_dense = max((c.score for c in chunks), default=0.0)
    has_lexical = any(c.lexical_score > 0 for c in chunks)
    return best_dense >= settings.retrieval_min_score or has_lexical


async def _hydrate(
    session: AsyncSession, workspace_id: uuid.UUID, chunk_ids: list[uuid.UUID]
) -> tuple[dict[uuid.UUID, DocumentChunk], dict[uuid.UUID, str]]:
    if not chunk_ids:
        return {}, {}
    rows = await session.execute(
        select(DocumentChunk).where(
            DocumentChunk.id.in_(chunk_ids),
            DocumentChunk.workspace_id == workspace_id,  # defense in depth
        )
    )
    by_id = {r.id: r for r in rows.scalars()}
    doc_ids = {r.document_id for r in by_id.values()}
    names: dict[uuid.UUID, str] = {}
    if doc_ids:
        docs = await session.execute(select(Document).where(Document.id.in_(doc_ids)))
        names = {d.id: d.original_filename for d in docs.scalars()}
    return by_id, names


async def _lexical_search(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    query: str,
    top_n: int,
    document_ids: list[uuid.UUID] | None,
) -> list[tuple[DocumentChunk, float]]:
    terms = _terms(query)
    if not terms:
        return []
    stmt = select(DocumentChunk).where(
        DocumentChunk.workspace_id == workspace_id,
        or_(*[DocumentChunk.content.ilike(f"%{t}%") for t in terms]),
    )
    if document_ids:
        stmt = stmt.where(DocumentChunk.document_id.in_(document_ids))
    rows = list((await session.execute(stmt.limit(200))).scalars())

    scored: list[tuple[DocumentChunk, float]] = []
    for row in rows:
        lowered = row.content.lower()
        score = float(sum(lowered.count(t) for t in terms))
        if score > 0:
            scored.append((row, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]


async def retrieve(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    query: str,
    embedder: EmbeddingProvider,
    vector_store: VectorStore,
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
    hybrid: bool | None = None,
) -> list[RetrievedChunk]:
    use_hybrid = settings.hybrid_enabled if hybrid is None else hybrid

    dense_n = max(top_k, settings.dense_top_n) if use_hybrid else top_k
    query_vector = (await embedder.embed([query]))[0]
    dense_hits = await vector_store.search(
        workspace_id=workspace_id,
        vector=query_vector,
        top_k=dense_n,
        document_ids=document_ids,
    )
    lexical = (
        await _lexical_search(
            session,
            workspace_id=workspace_id,
            query=query,
            top_n=settings.lexical_top_n,
            document_ids=document_ids,
        )
        if use_hybrid
        else []
    )

    dense_ids = [uuid.UUID(h.chunk_id) for h in dense_hits]
    lexical_ids = [row.id for row, _ in lexical]
    all_ids = list(dict.fromkeys([*dense_ids, *lexical_ids]))
    by_id, names = await _hydrate(session, workspace_id, all_ids)

    dense_score = {uuid.UUID(h.chunk_id): h.score for h in dense_hits}
    dense_rank = {uuid.UUID(h.chunk_id): i + 1 for i, h in enumerate(dense_hits)}
    lexical_score = {row.id: s for row, s in lexical}
    lexical_rank = {row.id: i + 1 for i, (row, _) in enumerate(lexical)}

    if use_hybrid:
        k = settings.rrf_k
        fused: dict[uuid.UUID, float] = {}
        for cid in all_ids:
            value = 0.0
            if cid in dense_rank:
                value += 1.0 / (k + dense_rank[cid])
            if cid in lexical_rank:
                value += 1.0 / (k + lexical_rank[cid])
            fused[cid] = value
        ordered = sorted(all_ids, key=lambda c: fused[c], reverse=True)
        method = "hybrid"
    else:
        ordered = dense_ids
        fused = {cid: dense_score.get(cid, 0.0) for cid in ordered}
        method = "vector"

    results: list[RetrievedChunk] = []
    for cid in ordered[:top_k]:
        row = by_id.get(cid)
        if row is None:
            continue
        results.append(
            RetrievedChunk(
                chunk_id=str(cid),
                document_id=str(row.document_id),
                document_filename=names.get(row.document_id, "document"),
                page_number=row.page_number,
                content=row.content,
                score=dense_score.get(cid, 0.0),
                chunk_index=row.chunk_index,
                lexical_score=lexical_score.get(cid, 0.0),
                fused_score=fused.get(cid, 0.0),
                dense_rank=dense_rank.get(cid),
                lexical_rank=lexical_rank.get(cid),
                method=method,
            )
        )
    return results
