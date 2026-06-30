"""Public API: API-key auth, document listing, ask, and the rate-limit logic."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from doc007.core.deps import get_embedder_dep, get_llm_dep, get_vector_store_dep
from doc007.main import app
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.providers.llm import MockLLMProvider
from tests.conftest import FakeVectorStore, register_and_login

API = "/api/v1"
PUBLIC = "/api/public/v1"


@pytest.fixture
def rag_overrides() -> Generator[None, None, None]:
    app.dependency_overrides[get_embedder_dep] = lambda: MockEmbeddingProvider(16)
    app.dependency_overrides[get_llm_dep] = lambda: MockLLMProvider()
    app.dependency_overrides[get_vector_store_dep] = FakeVectorStore
    yield
    for dep in (get_embedder_dep, get_llm_dep, get_vector_store_dep):
        app.dependency_overrides.pop(dep, None)


async def _key(client: AsyncClient, headers: dict) -> tuple[str, str]:
    ws = await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=headers)
    wid = ws.json()["id"]
    created = await client.post(
        f"{API}/workspaces/{wid}/api-keys", json={"name": "k"}, headers=headers
    )
    return wid, created.json()["key"]


async def test_public_requires_valid_key(client: AsyncClient) -> None:
    # No key -> 401.
    assert (await client.get(f"{PUBLIC}/documents")).status_code == 401
    # Bogus key -> 401.
    assert (
        await client.get(f"{PUBLIC}/documents", headers={"Authorization": "Bearer nope"})
    ).status_code == 401


async def test_public_documents_and_revocation(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid, raw = await _key(client, owner)
    api_headers = {"Authorization": f"Bearer {raw}"}

    listed = await client.get(f"{PUBLIC}/documents", headers=api_headers)
    assert listed.status_code == 200
    assert listed.json() == []  # empty workspace

    # Revoke the key via the app API; the public API then rejects it.
    keys = await client.get(f"{API}/workspaces/{wid}/api-keys", headers=owner)
    key_id = keys.json()[0]["id"]
    await client.delete(f"{API}/workspaces/{wid}/api-keys/{key_id}", headers=owner)
    assert (await client.get(f"{PUBLIC}/documents", headers=api_headers)).status_code == 401


async def test_public_ask(client: AsyncClient, rag_overrides: None) -> None:
    owner = await register_and_login(client, "owner@example.com")
    _, raw = await _key(client, owner)
    api_headers = {"Authorization": f"Bearer {raw}"}

    resp = await client.post(
        f"{PUBLIC}/ask", json={"question": "What is the policy?"}, headers=api_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # No documents in the workspace -> grounded refusal.
    assert body["not_found"] is True
    assert body["citations"] == []


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, int] = {}

    async def incr(self, k: str) -> int:
        self.store[k] = self.store.get(k, 0) + 1
        return self.store[k]

    async def expire(self, k: str, seconds: int) -> bool:
        return True


async def test_rate_limit_window() -> None:
    from doc007.core.rate_limit import allow

    redis = _FakeRedis()
    # Same time window -> 4th request within a limit of 3 is rejected.
    results = [
        await allow(redis, key="key-1", limit=3, window_seconds=60) for _ in range(5)
    ]
    assert results == [True, True, True, False, False]
