"""Chat API tests: ask (not-found path), conversation lifecycle, isolation."""

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


@pytest.fixture
def rag_overrides() -> Generator[None, None, None]:
    app.dependency_overrides[get_embedder_dep] = lambda: MockEmbeddingProvider(16)
    app.dependency_overrides[get_llm_dep] = lambda: MockLLMProvider()
    app.dependency_overrides[get_vector_store_dep] = FakeVectorStore
    yield
    for dep in (get_embedder_dep, get_llm_dep, get_vector_store_dep):
        app.dependency_overrides.pop(dep, None)


async def _workspace(client: AsyncClient, headers: dict, name: str = "Acme") -> str:
    resp = await client.post(f"{API}/workspaces", json={"name": name}, headers=headers)
    return resp.json()["id"]


async def test_ask_not_found_and_history(client: AsyncClient, rag_overrides: None) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, h)

    ask = await client.post(
        f"{API}/workspaces/{wid}/chat/ask",
        json={"question": "What is the refund policy?"},
        headers=h,
    )
    assert ask.status_code == 200, ask.text
    body = ask.json()
    # No documents ingested -> grounded refusal, no citations.
    assert body["not_found"] is True
    assert body["citations"] == []
    conversation_id = body["conversation_id"]

    convs = await client.get(f"{API}/workspaces/{wid}/chat/conversations", headers=h)
    assert len(convs.json()) == 1

    detail = await client.get(
        f"{API}/workspaces/{wid}/chat/conversations/{conversation_id}", headers=h
    )
    msgs = detail.json()["messages"]
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert msgs[0]["content"] == "What is the refund policy?"

    deleted = await client.delete(
        f"{API}/workspaces/{wid}/chat/conversations/{conversation_id}", headers=h
    )
    assert deleted.status_code == 204


async def test_chat_isolation(client: AsyncClient, rag_overrides: None) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = await _workspace(client, alice, "Alice Co")

    # Bob is not a member -> cannot ask or list in Alice's workspace.
    ask = await client.post(
        f"{API}/workspaces/{wid}/chat/ask", json={"question": "hi"}, headers=bob
    )
    assert ask.status_code == 404
    assert (
        await client.get(f"{API}/workspaces/{wid}/chat/conversations", headers=bob)
    ).status_code == 404
