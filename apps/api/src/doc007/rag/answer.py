"""Answer orchestration: retrieve -> guardrail -> prompt -> LLM -> citations."""

from __future__ import annotations

import re
import time
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.providers.base import ChatMessage, EmbeddingProvider, LLMProvider
from doc007.rag.prompt import NOT_FOUND, build_messages
from doc007.rag.retrieval import RetrievedChunk, passes_guardrail, retrieve
from doc007.rag.vector_store import VectorStore

_CITATION_RE = re.compile(r"\[(\d+)\]")
_SNIPPET_LEN = 300


@dataclass
class Citation:
    index: int
    document_id: str
    document_filename: str
    page_number: int | None
    snippet: str
    score: float
    chunk_id: str
    rank: int


@dataclass
class AnswerResult:
    answer: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: list[RetrievedChunk] = field(default_factory=list)
    not_found: bool = False
    coverage: str = "none"
    model: str = ""
    tokens_prompt: int = 0
    tokens_completion: int = 0
    latency_ms: int = 0


def _coverage(chunks: list[RetrievedChunk], cited: int) -> str:
    if not chunks or cited == 0:
        return "none"
    top = max((c.score for c in chunks), default=0.0)
    if top >= 0.6:
        return "high"
    if top >= 0.4:
        return "medium"
    return "low"


async def generate_answer(
    session: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    question: str,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    vector_store: VectorStore,
    history: list[ChatMessage] | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> AnswerResult:
    chunks = await retrieve(
        session,
        workspace_id=workspace_id,
        query=question,
        embedder=embedder,
        vector_store=vector_store,
        top_k=settings.retrieval_top_k,
        document_ids=document_ids,
    )

    # Guardrail: weak/empty retrieval -> refuse instead of calling the LLM.
    if not passes_guardrail(chunks):
        return AnswerResult(
            answer=NOT_FOUND, retrieved=chunks, not_found=True, coverage="none", model=llm.name
        )

    messages = build_messages(question, chunks, history)
    started = time.monotonic()
    result = await llm.complete(messages)
    latency_ms = int((time.monotonic() - started) * 1000)

    answer = result.content.strip()
    model_said_not_found = answer.lower().startswith("i couldn't find")

    cited_indexes = sorted(
        {int(m) for m in _CITATION_RE.findall(answer) if 1 <= int(m) <= len(chunks)}
    )
    citations: list[Citation] = []
    for rank, idx in enumerate(cited_indexes):
        c = chunks[idx - 1]
        citations.append(
            Citation(
                index=idx,
                document_id=c.document_id,
                document_filename=c.document_filename,
                page_number=c.page_number,
                snippet=c.content[:_SNIPPET_LEN],
                score=c.score,
                chunk_id=c.chunk_id,
                rank=rank,
            )
        )

    return AnswerResult(
        answer=answer,
        citations=citations,
        retrieved=chunks,
        not_found=model_said_not_found,
        coverage=_coverage(chunks, len(citations)),
        model=result.model,
        tokens_prompt=result.prompt_tokens,
        tokens_completion=result.completion_tokens,
        latency_ms=latency_ms,
    )
