"""Redis-backed JWT revocation list.

Logout and refresh-token rotation add a token's `jti` here so it is rejected
before its natural expiry. Entries auto-expire after the token would have
expired anyway. Fails open (treats tokens as not-revoked) if Redis is
unavailable, so a Redis outage degrades to "tokens live until expiry" rather
than locking everyone out.
"""

from __future__ import annotations

from doc007.core.config import settings
from doc007.core.logging import get_logger

log = get_logger(__name__)

_PREFIX = "bl:"


async def _client():
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.redis_url)


async def revoke(jti: str, ttl_seconds: int) -> None:
    """Mark a token id as revoked for the remainder of its lifetime."""
    if not jti or ttl_seconds <= 0:
        return
    try:
        client = await _client()
        try:
            await client.set(f"{_PREFIX}{jti}", "1", ex=ttl_seconds)
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        log.warning("token_blocklist_unavailable", action="revoke", error=str(exc))


async def is_revoked(jti: str) -> bool:
    """True if this token id has been revoked. Fail-open on any Redis error."""
    if not jti:
        return False
    try:
        client = await _client()
        try:
            return bool(await client.exists(f"{_PREFIX}{jti}"))
        finally:
            await client.aclose()
    except Exception as exc:  # noqa: BLE001
        log.warning("token_blocklist_unavailable", action="is_revoked", error=str(exc))
        return False
