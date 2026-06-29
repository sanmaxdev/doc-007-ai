"""Document ingestion pipeline (the async state machine).

extract -> clean -> chunk -> embed -> store. Status is persisted at each step
so the UI can follow progress, and failures are captured on the document.

Dependencies (storage, embedder, vector_store) are injected so the pipeline
is unit-testable with fakes and has no hard dependency on Qdrant/OpenAI.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.logging import get_logger
from doc007.db.models.document import Document, DocumentChunk, DocumentStatus
from doc007.providers.base import EmbeddingProvider
from doc007.rag.chunking import chunk_pages
from doc007.rag.cleaning import clean_text
from doc007.rag.extraction import Page, extract
from doc007.rag.vector_store import VectorPoint, VectorStore
from doc007.storage.base import Storage

log = get_logger(__name__)


class IngestionError(Exception):
    pass


async def ingest_document(
    session: AsyncSession,
    document_id: uuid.UUID,
    *,
    storage: Storage,
    embedder: EmbeddingProvider,
    vector_store: VectorStore,
) -> None:
    doc = await session.get(Document, document_id)
    if doc is None:
        log.warning("ingest_missing_document", document_id=str(document_id))
        return

    try:
        doc.status = DocumentStatus.extracting
        doc.error_message = None
        await session.commit()

        data = storage.load(doc.storage_key)
        pages = extract(data, mime_type=doc.mime_type, filename=doc.original_filename)
        cleaned = [Page(number=p.number, text=clean_text(p.text)) for p in pages]
        page_count = sum(1 for p in pages if p.number is not None) or None

        doc.status = DocumentStatus.chunking
        await session.commit()

        chunks = chunk_pages(cleaned)
        if not chunks:
            raise IngestionError("No extractable text found in document.")

        # Make sure the collection exists before any Qdrant op (first-ever ingest
        # would otherwise 404 on the delete below).
        await vector_store.ensure_collection()

        # Idempotent reprocess: clear previous chunks + vectors first.
        await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))
        await vector_store.delete_document(doc.workspace_id, doc.id)

        rows = [
            DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc.id,
                workspace_id=doc.workspace_id,
                chunk_index=c.chunk_index,
                content=c.content,
                token_count=c.token_count,
                page_number=c.page_number,
                char_start=c.char_start,
                char_end=c.char_end,
                embedding_model=embedder.name,
            )
            for c in chunks
        ]
        session.add_all(rows)

        doc.status = DocumentStatus.embedding
        await session.commit()

        vectors = await embedder.embed([c.content for c in chunks])
        points = [
            VectorPoint(
                id=str(row.id),
                vector=vector,
                payload={
                    "workspace_id": str(doc.workspace_id),
                    "document_id": str(doc.id),
                    "chunk_id": str(row.id),
                    "page_number": row.page_number,
                    "chunk_index": row.chunk_index,
                },
            )
            for row, vector in zip(rows, vectors, strict=True)
        ]
        await vector_store.upsert(points)

        doc.page_count = page_count
        doc.chunk_count = len(rows)
        doc.status = DocumentStatus.ready
        doc.processed_at = datetime.now(UTC)
        await session.commit()
        log.info("ingest_ready", document_id=str(doc.id), chunks=len(rows))
    except Exception as exc:  # noqa: BLE001 - record failure on the document
        await session.rollback()
        failed = await session.get(Document, document_id)
        if failed is not None:
            failed.status = DocumentStatus.failed
            failed.error_message = str(exc)[:1000]
            await session.commit()
        log.error("ingest_failed", document_id=str(document_id), error=str(exc))
