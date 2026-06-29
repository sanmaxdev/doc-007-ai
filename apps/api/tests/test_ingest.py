"""Ingestion pipeline integration tests (mock embedder + fake vector store)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from doc007.db.models.document import Document, DocumentStatus
from doc007.db.models.user import User
from doc007.db.models.workspace import Workspace
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.rag.ingest import ingest_document
from doc007.storage.local import LocalStorage
from tests.conftest import FakeVectorStore


async def _seed_document(session: AsyncSession, storage: LocalStorage, content: bytes) -> Document:
    user = User(email=f"{uuid.uuid4().hex}@example.com", hashed_password="x")
    session.add(user)
    await session.flush()

    ws = Workspace(name="W", slug=f"w-{uuid.uuid4().hex[:8]}", owner_id=user.id)
    session.add(ws)
    await session.flush()

    key = f"{ws.id}/{uuid.uuid4().hex}.txt"
    storage.save(key, content)
    doc = Document(
        workspace_id=ws.id,
        uploaded_by=user.id,
        filename="notes.txt",
        original_filename="notes.txt",
        storage_key=key,
        mime_type="text/plain",
        file_size_bytes=len(content),
        checksum_sha256="x" * 64,
        status=DocumentStatus.uploaded,
    )
    session.add(doc)
    await session.commit()
    return doc


async def test_ingest_success(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    doc = await _seed_document(session, storage, ("This is a sentence. " * 300).encode())
    store = FakeVectorStore()

    await ingest_document(
        session,
        doc.id,
        storage=storage,
        embedder=MockEmbeddingProvider(16),
        vector_store=store,
    )

    await session.refresh(doc)
    assert doc.status == DocumentStatus.ready
    assert doc.chunk_count > 0
    assert len(store.points) == doc.chunk_count
    # Every vector carries the workspace_id payload (vector-layer isolation parity).
    assert all(
        p.payload["workspace_id"] == str(doc.workspace_id) for p in store.points.values()
    )


async def test_ingest_empty_document_fails(session: AsyncSession, tmp_path) -> None:
    storage = LocalStorage(str(tmp_path))
    doc = await _seed_document(session, storage, b"   \n\n   \n  ")

    await ingest_document(
        session,
        doc.id,
        storage=storage,
        embedder=MockEmbeddingProvider(16),
        vector_store=FakeVectorStore(),
    )

    await session.refresh(doc)
    assert doc.status == DocumentStatus.failed
    assert doc.error_message
