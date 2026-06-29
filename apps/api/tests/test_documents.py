"""Document API tests: lifecycle, isolation, validation.

Storage, the task enqueuer, and the vector store are overridden so the HTTP
layer is tested without touching disk paths, Redis, or Qdrant.
"""

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
def overrides(tmp_path) -> Generator[dict, None, None]:
    calls: list[str] = []
    storage = LocalStorage(str(tmp_path))
    store = FakeVectorStore()

    def recorder(document_id) -> None:
        calls.append(str(document_id))

    app.dependency_overrides[get_storage_dep] = lambda: storage
    app.dependency_overrides[get_vector_store_dep] = lambda: store
    app.dependency_overrides[get_enqueue_ingestion] = lambda: recorder
    yield {"calls": calls, "storage": storage, "store": store}
    for dep in (get_storage_dep, get_vector_store_dep, get_enqueue_ingestion):
        app.dependency_overrides.pop(dep, None)


async def _new_workspace(client: AsyncClient, headers: dict, name: str = "Acme") -> str:
    resp = await client.post(f"{API}/workspaces", json={"name": name}, headers=headers)
    return resp.json()["id"]


async def test_document_lifecycle(client: AsyncClient, overrides: dict) -> None:
    h = await register_and_login(client, "owner@example.com")
    wid = await _new_workspace(client, h)

    files = {"file": ("notes.txt", b"hello world content for the document", "text/plain")}
    up = await client.post(f"{API}/workspaces/{wid}/documents", files=files, headers=h)
    assert up.status_code == 201, up.text
    doc = up.json()
    assert doc["status"] == "uploaded"
    assert doc["original_filename"] == "notes.txt"
    assert overrides["calls"] == [doc["id"]]  # ingestion was enqueued

    listed = await client.get(f"{API}/workspaces/{wid}/documents", headers=h)
    assert len(listed.json()) == 1

    got = await client.get(f"{API}/workspaces/{wid}/documents/{doc['id']}", headers=h)
    assert got.status_code == 200

    rep = await client.post(
        f"{API}/workspaces/{wid}/documents/{doc['id']}/reprocess", headers=h
    )
    assert rep.status_code == 200 and rep.json()["status"] == "uploaded"
    assert len(overrides["calls"]) == 2

    deleted = await client.delete(f"{API}/workspaces/{wid}/documents/{doc['id']}", headers=h)
    assert deleted.status_code == 204
    assert len((await client.get(f"{API}/workspaces/{wid}/documents", headers=h)).json()) == 0


async def test_document_isolation(client: AsyncClient, overrides: dict) -> None:
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")
    wid = await _new_workspace(client, alice, "Alice Co")

    files = {"file": ("secret.txt", b"alice confidential content", "text/plain")}
    resp = await client.post(f"{API}/workspaces/{wid}/documents", files=files, headers=alice)
    doc = resp.json()

    # Bob is not a member: list and get both 404
    assert (await client.get(f"{API}/workspaces/{wid}/documents", headers=bob)).status_code == 404
    assert (
        await client.get(f"{API}/workspaces/{wid}/documents/{doc['id']}", headers=bob)
    ).status_code == 404


async def test_upload_rejects_unsupported_type(client: AsyncClient, overrides: dict) -> None:
    h = await register_and_login(client, "c@example.com")
    wid = await _new_workspace(client, h)
    files = {"file": ("malware.exe", b"MZ\x90\x00", "application/octet-stream")}
    r = await client.post(f"{API}/workspaces/{wid}/documents", files=files, headers=h)
    assert r.status_code == 400
