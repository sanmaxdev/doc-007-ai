"""Auth hardening: token jti, logout revocation, refresh rotation, prod guard.

Token revocation is backed by Redis in production; here the blocklist is swapped
for an in-memory set so the behavior is deterministic without a Redis server.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from doc007 import main
from doc007.core import token_blocklist
from doc007.core.config import settings
from doc007.core.security import create_access_token, decode_token, token_ttl_seconds

API = "/api/v1"


@pytest.fixture
def memory_blocklist(monkeypatch) -> set[str]:
    store: set[str] = set()

    async def fake_revoke(jti: str, ttl_seconds: int) -> None:
        if jti and ttl_seconds > 0:
            store.add(jti)

    async def fake_is_revoked(jti: str) -> bool:
        return jti in store

    monkeypatch.setattr(token_blocklist, "revoke", fake_revoke)
    monkeypatch.setattr(token_blocklist, "is_revoked", fake_is_revoked)
    return store


def test_access_token_has_jti_and_ttl() -> None:
    payload = decode_token(create_access_token("user-1"))
    assert payload is not None
    assert payload["type"] == "access"
    assert payload.get("jti")
    assert token_ttl_seconds(payload) > 0


async def test_logout_revokes_tokens(client: AsyncClient, memory_blocklist: set[str]) -> None:
    await client.post(
        f"{API}/auth/register",
        json={"email": "rev@example.com", "password": "password123"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "rev@example.com", "password": "password123"}
    )
    access = login.json()["access_token"]
    refresh = login.json()["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    # The token works before logout.
    assert (await client.get(f"{API}/auth/me", headers=headers)).status_code == 200

    out = await client.post(
        f"{API}/auth/logout", headers=headers, json={"refresh_token": refresh}
    )
    assert out.status_code == 200

    # Both tokens are rejected after logout.
    assert (await client.get(f"{API}/auth/me", headers=headers)).status_code == 401
    reused = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert reused.status_code == 401


async def test_refresh_token_rotation(client: AsyncClient, memory_blocklist: set[str]) -> None:
    await client.post(
        f"{API}/auth/register",
        json={"email": "rot@example.com", "password": "password123"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "rot@example.com", "password": "password123"}
    )
    old_refresh = login.json()["refresh_token"]

    first = await client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert first.status_code == 200
    new_refresh = first.json()["refresh_token"]

    # The old refresh token is single-use and is rejected on reuse.
    again = await client.post(f"{API}/auth/refresh", json={"refresh_token": old_refresh})
    assert again.status_code == 401

    # The rotated token works.
    ok = await client.post(f"{API}/auth/refresh", json={"refresh_token": new_refresh})
    assert ok.status_code == 200


def test_production_safety_guard(monkeypatch) -> None:
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "debug", False)

    monkeypatch.setattr(settings, "jwt_secret_key", "change-me")
    with pytest.raises(RuntimeError):
        main._check_production_safety()

    # A strong secret passes.
    monkeypatch.setattr(settings, "jwt_secret_key", "x" * 32)
    main._check_production_safety()

    # Debug must be off in production.
    monkeypatch.setattr(settings, "debug", True)
    with pytest.raises(RuntimeError):
        main._check_production_safety()
