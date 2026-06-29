"""RAG unit/integration tests: prompt safety, not-found guardrail, answer + citations."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from doc007.db.models.document import Document, DocumentStatus
from doc007.db.models.user import User
from doc007.db.models.workspace import Workspace
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.providers.llm import MockLLMProvider
from doc007.rag.answer import generate_answer
from doc007.rag.ingest import ingest_document
from doc007.rag.prompt import NOT_FOUND, build_messages
from doc007.rag.retrieval import RetrievedChunk
from doc007.storage.local import LocalStorage
from tests.conftest import FakeVectorStore


def test_prompt_wraps_context_and_defends_injection() -> None:
    chunks = [
        RetrievedChunk(
            chunk_id="c1",
            document_id="d1",
            document_filename="policy.pdf",
            page_number=3,
            content="Vacation is 20 days.",
            score=0.9,
        )
    ]
    messages = build_messages("How many vacation days?", chunks)
    assert messages[0].role == "system"
    assert "untrusted" in messages[0].content.lower()
    user = messages[-1].content
    assert "<context>" in user and "[1]" in user
    assert 'policy.pdf' in user and "p.3" in user


async def test_answer_not_found_without_context(session: AsyncSession) -> None:
    result = await generate_answer(
        session,
        workspace_id=uuid.uuid4(),
        question="anything",
        embedder=MockEmbeddingProvider(16),
        llm=MockLLMProvider(),
        vector_store=FakeVectorStore(),  # empty -> no hits
    )
    assert result.not_found is True
    assert result.answer == NOT_FOUND
    assert result.citations == []
    assert result.coverage == "none"


async def _seed_and_ingest(session: AsyncSession, storage: LocalStorage, store: FakeVectorStore):
    user = User(email=f"{uuid.uuid4().hex}@e.com", hashed_password="x")
    session.add(user)
    await session.flush()
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    session.add(ws)
    await session.flush()
    key = f"{ws.id}/{uuid.uuid4().hex}.txt"
    storage.save(key, ("The vacation policy grants 20 days per year. " * 80).encode())
    doc = Document(
        workspace_id=ws.id,
        uploaded_by=user.id,
        filename="p.txt",
        original_filename="policy.txt",
        storage_key=key,
        mime_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="z" * 64,
        status=DocumentStatus.uploaded,
    )
    session.add(doc)
    await session.commit()
    await ingest_document(
        session, doc.id, storage=storage, embedder=MockEmbeddingProvider(16), vector_store=store
    )
    return ws


async def test_answer_with_citations(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    store = FakeVectorStore()
    ws = await _seed_and_ingest(session, storage, store)

    result = await generate_answer(
        session,
        workspace_id=ws.id,
        question="How many vacation days do we get?",
        embedder=MockEmbeddingProvider(16),
        llm=MockLLMProvider(),
        vector_store=store,
    )

    assert result.not_found is False
    assert result.retrieved, "expected retrieved chunks"
    assert result.citations, "mock LLM cites [1], so a citation should map"
    assert result.citations[0].document_filename == "policy.txt"
    assert result.coverage in {"high", "medium", "low"}
