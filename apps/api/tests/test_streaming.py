"""Streaming answers over SSE (POST /chat/ask/stream)."""

from __future__ import annotations

import json
from collections.abc import Generator

import pytest
from httpx import AsyncClient

from doc007.core.deps import get_embedder_dep, get_llm_dep, get_vector_store_dep
from doc007.main import app
from doc007.providers.embeddings import MockEmbeddingProvider
from doc007.providers.llm import MockLLMProvider
from tests.conftest import FakeVectorStore, register_and_login

API = "/api/v1"


@pytest.fixture
def rag_overrides() -> Generator[None, None, None]:
    app.dependency_overrides[get_embedder_dep] = lambda: MockEmbeddingProvider(16)
    app.dependency_overrides[get_llm_dep] = lambda: MockLLMProvider()
    app.dependency_overrides[get_vector_store_dep] = FakeVectorStore
    yield
    for dep in (get_embedder_dep, get_llm_dep, get_vector_store_dep):
        app.dependency_overrides.pop(dep, None)


async def _collect(client: AsyncClient, url: str, headers: dict, body: dict) -> list[dict]:
    events: list[dict] = []
    async with client.stream("POST", url, json=body, headers=headers) as resp:
        assert resp.status_code == 200, resp.status_code
        assert resp.headers["content-type"].startswith("text/event-stream")
        async for line in resp.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[len("data: ") :]))
    return events


async def test_stream_emits_tokens_then_done(client: AsyncClient, rag_overrides: None) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=h)).json()["id"]

    events = await _collect(
        client,
        f"{API}/workspaces/{wid}/chat/ask/stream",
        h,
        {"question": "What is the refund policy?"},
    )
    types = [e["type"] for e in events]
    assert "token" in types
    assert types[-1] == "done"

    done = events[-1]
    # No documents -> grounded refusal, streamed and persisted.
    assert done["not_found"] is True
    assert done["citations"] == []

    detail = await client.get(
        f"{API}/workspaces/{wid}/chat/conversations/{done['conversation_id']}", headers=h
    )
    assert [m["role"] for m in detail.json()["messages"]] == ["user", "assistant"]


async def test_stream_isolation(client: AsyncClient, rag_overrides: None) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "A"}, headers=alice)).json()["id"]

    async with client.stream(
        "POST",
        f"{API}/workspaces/{wid}/chat/ask/stream",
        json={"question": "secrets?"},
        headers=bob,
    ) as resp:
        assert resp.status_code == 404
