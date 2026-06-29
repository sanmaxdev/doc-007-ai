"""Celery tasks: the async document ingestion pipeline.

Celery runs tasks synchronously, so the async ingestion is driven via
asyncio.run on a fresh engine (NullPool) per task to keep the event loop and
connection pool lifecycles clean.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from doc007.core.config import settings
from doc007.core.logging import get_logger
from doc007.providers.embeddings import get_embedding_provider
from doc007.rag.ingest import ingest_document
from doc007.rag.vector_store import get_vector_store
from doc007.storage import get_storage
from doc007.workers.celery_app import celery_app

log = get_logger(__name__)


async def _run(document_id: uuid.UUID) -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            await ingest_document(
                session,
                document_id,
                storage=get_storage(),
                embedder=get_embedding_provider(),
                vector_store=get_vector_store(),
            )
    finally:
        await engine.dispose()


@celery_app.task(name="doc007.process_document")
def process_document(document_id: str) -> str:
    log.info("process_document", document_id=document_id)
    asyncio.run(_run(uuid.UUID(document_id)))
    return document_id
