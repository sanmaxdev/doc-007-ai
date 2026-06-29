"""Liveness and readiness endpoints.

`/healthz`  — liveness: the process is up (no external deps).
`/readyz`   — readiness: can we reach Postgres, Redis, and Qdrant?
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import text

from doc007 import __version__
from doc007.core.config import settings
from doc007.core.logging import get_logger
from doc007.db.base import engine

router = APIRouter(tags=["health"])
log = get_logger(__name__)


@router.get("/healthz", summary="Liveness probe")
async def healthz() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": __version__}


@router.get("/readyz", summary="Readiness probe")
async def readyz() -> dict:
    checks: dict[str, str] = {}

    # Postgres
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"error: {type(exc).__name__}"

    # Redis
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url)
        await client.ping()
        await client.aclose()
        checks["redis"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {type(exc).__name__}"

    # Qdrant
    try:
        from qdrant_client import AsyncQdrantClient

        qc = AsyncQdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
        await qc.get_collections()
        await qc.close()
        checks["qdrant"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["qdrant"] = f"error: {type(exc).__name__}"

    ready = all(v == "ok" for v in checks.values())
    return {"status": "ready" if ready else "degraded", "checks": checks}
