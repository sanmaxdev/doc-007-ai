"""Retrieval debug/eval: run retrieval and surface scores + the would-be prompt.

No LLM call — this is the developer/eval view of what the RAG pipeline retrieves
and how it would be prompted.
"""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.providers.base import EmbeddingProvider
from doc007.rag.prompt import build_messages
from doc007.rag.retrieval import RetrievedChunk, passes_guardrail, retrieve
from doc007.rag.vector_store import VectorStore


async def debug_retrieve(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    question: str,
    embedder: EmbeddingProvider,
    vector_store: VectorStore,
    top_k: int,
    document_ids: list[uuid.UUID] | None = None,
    hybrid: bool | None = None,
) -> tuple[list[RetrievedChunk], str, bool, str]:
    chunks = await retrieve(
        session,
        workspace_id=workspace_id,
        query=question,
        embedder=embedder,
        vector_store=vector_store,
        top_k=top_k,
        document_ids=document_ids,
        hybrid=hybrid,
    )
    messages = build_messages(question, chunks)
    prompt = "\n\n".join(f"[{m.role}]\n{m.content}" for m in messages)
    not_found = not passes_guardrail(chunks)
    use_hybrid = settings.hybrid_enabled if hybrid is None else hybrid
    method = chunks[0].method if chunks else ("hybrid" if use_hybrid else "vector")
    return chunks, prompt, not_found, method
