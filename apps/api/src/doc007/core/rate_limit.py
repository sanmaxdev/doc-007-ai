"""Fixed-window rate limiting backed by Redis.

Used by the public API (per API key). Fails open if Redis is unavailable so a
Redis outage degrades to "unlimited" rather than taking the API down.
"""

from __future__ import annotations

import time

from doc007.core.config import settings
from doc007.core.logging import get_logger

log = get_logger(__name__)


async def allow(client, *, key: str, limit: int, window_seconds: int) -> bool:
    """Increment the current window's counter and report whether it's within limit."""
    bucket = int(time.time() // window_seconds)
    redis_key = f"rl:{key}:{bucket}"
    count = await client.incr(redis_key)
    if count == 1:
        await client.expire(redis_key, window_seconds)
    return count <= limit


async def enforce(
    *, key: str, limit: int | None = None, window_seconds: int | None = None
) -> bool:
    """Return True if the request is allowed. Fail-open on any Redis error."""
    limit = limit if limit is not None else settings.public_rate_limit
    window_seconds = window_seconds or settings.public_rate_window_seconds
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(settings.redis_url)
        try:
            return await allow(client, key=key, limit=limit, window_seconds=window_seconds)
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        log.warning("rate_limit_unavailable", error=str(exc))
        return True
