"""Document tags: create, list, filter, remove."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from doc007.core.deps import (
    get_enqueue_ingestion,
    get_storage_dep,
    get_vector_store_dep,
)
from doc007.main import app
from doc007.storage.local import LocalStorage
from tests.conftest import FakeVectorStore, register_and_login

API = "/api/v1"


@pytest.fixture
def overrides(tmp_path) -> Generator[None, None, None]:
    app.dependency_overrides[get_storage_dep] = lambda: LocalStorage(str(tmp_path))
    app.dependency_overrides[get_vector_store_dep] = FakeVectorStore
    app.dependency_overrides[get_enqueue_ingestion] = lambda: (lambda _id: None)
    yield
    for dep in (get_storage_dep, get_vector_store_dep, get_enqueue_ingestion):
        app.dependency_overrides.pop(dep, None)


async def _workspace(client: AsyncClient, headers: dict) -> str:
    resp = await client.post(f"{API}/workspaces", json={"name": "Acme"}, headers=headers)
    return resp.json()["id"]


async def _upload(client, headers, wid, name="notes.txt") -> str:
    files = {"file": (name, b"some content for the document body", "text/plain")}
    resp = await client.post(f"{API}/workspaces/{wid}/documents", files=files, headers=headers)
    return resp.json()["id"]


async def test_tag_lifecycle_and_filter(client: AsyncClient, overrides: None) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, h)
    doc_id = await _upload(client, h, wid)
    other_id = await _upload(client, h, wid, "other.txt")

    # Add two tags (names are normalized to lowercase).
    r = await client.post(
        f"{API}/workspaces/{wid}/documents/{doc_id}/tags", json={"name": "Finance"}, headers=h
    )
    assert r.status_code == 200
    assert [t["name"] for t in r.json()] == ["finance"]

    r = await client.post(
        f"{API}/workspaces/{wid}/documents/{doc_id}/tags", json={"name": "HR"}, headers=h
    )
    names = [t["name"] for t in r.json()]
    assert names == ["finance", "hr"]
    finance_id = next(t["id"] for t in r.json() if t["name"] == "finance")

    # Workspace tag list.
    tags = await client.get(f"{API}/workspaces/{wid}/tags", headers=h)
    assert {t["name"] for t in tags.json()} == {"finance", "hr"}

    # The document carries its tags.
    detail = await client.get(f"{API}/workspaces/{wid}/documents/{doc_id}", headers=h)
    assert {t["name"] for t in detail.json()["tags"]} == {"finance", "hr"}

    # Filtering by tag returns only the tagged document.
    filtered = await client.get(
        f"{API}/workspaces/{wid}/documents", params={"tag_id": finance_id}, headers=h
    )
    ids = [d["id"] for d in filtered.json()]
    assert ids == [doc_id] and other_id not in ids

    # Search by filename.
    found = await client.get(
        f"{API}/workspaces/{wid}/documents", params={"search": "other"}, headers=h
    )
    assert [d["id"] for d in found.json()] == [other_id]

    # Remove a tag.
    rm = await client.delete(
        f"{API}/workspaces/{wid}/documents/{doc_id}/tags/{finance_id}", headers=h
    )
    assert [t["name"] for t in rm.json()] == ["hr"]


async def test_tag_isolation(client: AsyncClient, overrides: None) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = await _workspace(client, alice)
    doc_id = await _upload(client, alice, wid)

    # Non-member cannot tag or list tags.
    assert (
        await client.post(
            f"{API}/workspaces/{wid}/documents/{doc_id}/tags",
            json={"name": "x"},
            headers=bob,
        )
    ).status_code == 404
    assert (await client.get(f"{API}/workspaces/{wid}/tags", headers=bob)).status_code == 404
