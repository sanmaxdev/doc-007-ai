"""Celery application.

Run a worker:
    celery -A doc007.workers.celery_app.celery_app worker --loglevel=info
"""

from __future__ import annotations

from celery import Celery

from doc007.core.config import settings

celery_app = Celery(
    "doc007",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["doc007.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_queue="default",
)


@celery_app.task(name="doc007.ping")
def ping() -> str:
    """Trivial task to verify the worker pipeline end-to-end."""
    return "pong"
