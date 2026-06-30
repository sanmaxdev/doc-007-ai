"""Per-workspace question quota enforcement and the usage summary."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_embedder_dep, get_llm_dep, get_vector_store_dep
from doc007.db.models.workspace import Workspace
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


async def test_quota_enforced_and_summary(
    client: AsyncClient, session: AsyncSession, rag_overrides: None
) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=h)).json()["id"]

    # Cap the workspace at 1 question/month directly on the row.
    ws = await session.get(Workspace, uuid.UUID(wid))
    assert ws is not None
    ws.monthly_question_limit = 1
    await session.commit()

    first = await client.post(
        f"{API}/workspaces/{wid}/chat/ask", json={"question": "first?"}, headers=h
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        f"{API}/workspaces/{wid}/chat/ask", json={"question": "second?"}, headers=h
    )
    assert second.status_code == 429
    assert second.json()["code"] == "quota_exceeded"

    usage = await client.get(f"{API}/workspaces/{wid}/usage", headers=h)
    assert usage.status_code == 200
    body = usage.json()
    assert body["questions_this_period"] == 1
    assert body["monthly_question_limit"] == 1


async def test_usage_isolation(client: AsyncClient) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = (await client.post(f"{API}/workspaces", json={"name": "A"}, headers=alice)).json()["id"]
    assert (await client.get(f"{API}/workspaces/{wid}/usage", headers=bob)).status_code == 404
