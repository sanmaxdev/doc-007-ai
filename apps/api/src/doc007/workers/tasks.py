"""Celery tasks.

Phase 2 will implement `process_document` here — the async ingestion
pipeline: extract -> clean -> chunk -> embed -> store (Qdrant) with the
document status state machine.
"""

from __future__ import annotations

from doc007.core.logging import get_logger
from doc007.workers.celery_app import celery_app

log = get_logger(__name__)


@celery_app.task(name="doc007.echo")
def echo(message: str) -> str:
    log.info("echo", message=message)
    return message
