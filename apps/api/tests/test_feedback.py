"""Answer feedback: submit, update (upsert), and isolation."""

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


async def _ask(client, headers, wid) -> str:
    resp = await client.post(
        f"{API}/workspaces/{wid}/chat/ask", json={"question": "anything?"}, headers=headers
    )
    return resp.json()["message_id"]


async def test_submit_and_update_feedback(client: AsyncClient, rag_overrides: None) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, h)
    message_id = await _ask(client, h, wid)

    up = await client.post(
        f"{API}/workspaces/{wid}/chat/messages/{message_id}/feedback",
        json={"rating": "helpful"},
        headers=h,
    )
    assert up.status_code == 200, up.text
    assert up.json()["rating"] == "helpful"

    # Re-submitting updates in place (unique per message+user).
    again = await client.post(
        f"{API}/workspaces/{wid}/chat/messages/{message_id}/feedback",
        json={"rating": "not_helpful", "comment": "missed the point"},
        headers=h,
    )
    assert again.status_code == 200
    assert again.json()["rating"] == "not_helpful"
    assert again.json()["message_id"] == message_id


async def test_feedback_not_found_and_isolation(client: AsyncClient, rag_overrides: None) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = await _workspace(client, alice)
    message_id = await _ask(client, alice, wid)

    # Unknown message id -> 404.
    import uuid

    assert (
        await client.post(
            f"{API}/workspaces/{wid}/chat/messages/{uuid.uuid4()}/feedback",
            json={"rating": "helpful"},
            headers=alice,
        )
    ).status_code == 404

    # Non-member cannot leave feedback in Alice's workspace -> 404.
    assert (
        await client.post(
            f"{API}/workspaces/{wid}/chat/messages/{message_id}/feedback",
            json={"rating": "helpful"},
            headers=bob,
        )
    ).status_code == 404
