"""Workspace analytics: answer rate, knowledge gaps, top docs, feedback."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_embedder_dep, get_llm_dep, get_vector_store_dep
from doc007.db.models.document import Document, DocumentStatus
from doc007.main import app
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.providers.llm import MockLLMProvider
from doc007.rag.ingest import ingest_document
from doc007.storage.local import LocalStorage
from tests.conftest import FakeVectorStore, register_and_login

API = "/api/v1"


@pytest.fixture
def rag_overrides() -> Generator[dict, None, None]:
    store, embedder = FakeVectorStore(), MockEmbeddingProvider(16)
    app.dependency_overrides[get_embedder_dep] = lambda: embedder
    app.dependency_overrides[get_llm_dep] = lambda: MockLLMProvider()
    app.dependency_overrides[get_vector_store_dep] = lambda: store
    yield {"store": store, "embedder": embedder}
    for dep in (get_embedder_dep, get_llm_dep, get_vector_store_dep):
        app.dependency_overrides.pop(dep, None)


async def _ws(client: AsyncClient, h: dict) -> str:
    return (await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=h)).json()["id"]


async def _ask(client, h, wid, q):
    resp = await client.post(f"{API}/workspaces/{wid}/chat/ask", json={"question": q}, headers=h)
    return resp.json()


async def _ingest_doc(session, workspace_id, store, embedder, storage) -> None:
    key = f"{workspace_id}/{uuid.uuid4().hex}.txt"
    storage.save(key, ("The vacation policy grants 20 days per year. " * 60).encode())
    doc = Document(
        workspace_id=workspace_id,
        uploaded_by=None,
        filename="p.txt",
        original_filename="policy.txt",
        storage_key=key,
        mime_type="text/plain",
        file_size_bytes=100,
        checksum_sha256=uuid.uuid4().hex * 2,
        status=DocumentStatus.uploaded,
    )
    session.add(doc)
    await session.commit()
    await ingest_document(session, doc.id, storage=storage, embedder=embedder, vector_store=store)


async def test_analytics_unanswered(client: AsyncClient, rag_overrides: dict) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _ws(client, h)

    # No documents -> both questions are unanswered (knowledge gaps).
    await _ask(client, h, wid, "What is the refund policy?")
    await _ask(client, h, wid, "Where is the office?")

    a = (await client.get(f"{API}/workspaces/{wid}/analytics", headers=h)).json()
    assert a["total_questions"] == 2
    assert a["answered"] == 0
    assert a["unanswered"] == 2
    assert a["answer_rate"] == 0.0
    assert len(a["unanswered_questions"]) == 2
    assert {q["question"] for q in a["recent_questions"]} == {
        "What is the refund policy?",
        "Where is the office?",
    }


async def test_analytics_answered_top_docs_feedback(
    client: AsyncClient, session: AsyncSession, rag_overrides: dict, tmp_path
) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _ws(client, h)
    await _ingest_doc(
        session,
        uuid.UUID(wid),
        rag_overrides["store"],
        rag_overrides["embedder"],
        LocalStorage(str(tmp_path)),
    )

    ans = await _ask(client, h, wid, "How many vacation days do we get?")
    assert ans["not_found"] is False
    await client.post(
        f"{API}/workspaces/{wid}/chat/messages/{ans['message_id']}/feedback",
        json={"rating": "helpful"},
        headers=h,
    )

    a = (await client.get(f"{API}/workspaces/{wid}/analytics", headers=h)).json()
    assert a["total_questions"] == 1
    assert a["answered"] == 1
    assert a["answer_rate"] == 1.0
    assert a["feedback_helpful"] == 1
    assert any(d["filename"] == "policy.txt" for d in a["top_documents"])


async def test_analytics_isolation(client: AsyncClient) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = await _ws(client, alice)
    assert (await client.get(f"{API}/workspaces/{wid}/analytics", headers=bob)).status_code == 404
