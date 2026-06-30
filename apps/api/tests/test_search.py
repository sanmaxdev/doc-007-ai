"""Hybrid retrieval (dense + lexical + RRF) and the debug /retrieve endpoint."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_embedder_dep, get_vector_store_dep
from doc007.db.models.document import Document, DocumentStatus
from doc007.db.models.user import User
from doc007.db.models.workspace import Workspace
from doc007.main import app
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.rag.ingest import ingest_document
from doc007.rag.retrieval import passes_guardrail, retrieve
from doc007.storage.local import LocalStorage
from tests.conftest import FakeVectorStore, register_and_login

API = "/api/v1"
_TEXT = "The vacation policy grants 20 days of paid leave per year. "


async def _ingest(session, workspace_id, storage, store, embedder) -> None:
    key = f"{workspace_id}/{uuid.uuid4().hex}.txt"
    storage.save(key, (_TEXT * 60).encode())
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


async def _seed_workspace(session: AsyncSession, storage, store, embedder) -> Workspace:
    user = User(email=f"{uuid.uuid4().hex}@e.com", hashed_password="x")
    session.add(user)
    await session.flush()
    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    session.add(ws)
    await session.flush()
    await _ingest(session, ws.id, storage, store, embedder)
    return ws


async def test_hybrid_returns_dense_and_lexical_scores(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    store, embedder = FakeVectorStore(), MockEmbeddingProvider(16)
    ws = await _seed_workspace(session, storage, store, embedder)

    chunks = await retrieve(
        session,
        workspace_id=ws.id,
        query="vacation days policy",
        embedder=embedder,
        vector_store=store,
        top_k=5,
        hybrid=True,
    )
    assert chunks
    assert chunks[0].method == "hybrid"
    assert any(c.lexical_score > 0 for c in chunks)  # keyword arm fired
    assert any(c.score > 0 for c in chunks)  # dense arm fired
    assert all(c.fused_score >= 0 for c in chunks)
    assert passes_guardrail(chunks)


async def test_lexical_recall_when_dense_is_empty(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    store, embedder = FakeVectorStore(), MockEmbeddingProvider(16)
    ws = await _seed_workspace(session, storage, store, embedder)

    empty_dense = FakeVectorStore()  # nothing indexed -> no dense hits
    chunks = await retrieve(
        session,
        workspace_id=ws.id,
        query="vacation leave",
        embedder=embedder,
        vector_store=empty_dense,
        top_k=5,
        hybrid=True,
    )
    assert chunks, "lexical search should still surface keyword matches"
    assert all(c.score == 0.0 for c in chunks)  # no dense contribution
    assert any(c.lexical_score > 0 for c in chunks)
    assert passes_guardrail(chunks)  # a literal keyword match is enough to answer


async def test_guardrail_blocks_when_nothing_matches(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    store, embedder = FakeVectorStore(), MockEmbeddingProvider(16)
    ws = await _seed_workspace(session, storage, store, embedder)

    chunks = await retrieve(
        session,
        workspace_id=ws.id,
        query="quarterly cryptocurrency taxation",
        embedder=embedder,
        vector_store=FakeVectorStore(),
        top_k=5,
        hybrid=True,
    )
    assert chunks == []
    assert passes_guardrail(chunks) is False


@pytest.fixture
def retrieval_overrides() -> Generator[dict, None, None]:
    store, embedder = FakeVectorStore(), MockEmbeddingProvider(16)
    app.dependency_overrides[get_embedder_dep] = lambda: embedder
    app.dependency_overrides[get_vector_store_dep] = lambda: store
    yield {"store": store, "embedder": embedder}
    for dep in (get_embedder_dep, get_vector_store_dep):
        app.dependency_overrides.pop(dep, None)


async def test_retrieve_endpoint(
    client: AsyncClient, session: AsyncSession, retrieval_overrides: dict, tmp_path
) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=h)).json()["id"]

    storage = LocalStorage(str(tmp_path))
    await _ingest(
        session,
        uuid.UUID(wid),
        storage,
        retrieval_overrides["store"],
        retrieval_overrides["embedder"],
    )

    r = await client.post(
        f"{API}/workspaces/{wid}/search/retrieve",
        json={"question": "How many vacation days?"},
        headers=h,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["not_found"] is False
    assert len(body["chunks"]) >= 1
    assert "<context>" in body["prompt"] and "untrusted" in body["prompt"].lower()
    first = body["chunks"][0]
    assert {"score", "lexical_score", "fused_score", "chunk_index"} <= first.keys()


async def test_retrieve_isolation(client: AsyncClient, retrieval_overrides: dict) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "A"}, headers=alice)).json()["id"]

    r = await client.post(
        f"{API}/workspaces/{wid}/search/retrieve",
        json={"question": "secrets?"},
        headers=bob,
    )
    assert r.status_code == 404
