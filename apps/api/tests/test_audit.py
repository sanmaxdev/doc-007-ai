"""Audit log recording and access control."""

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


async def _add_member(client, owner_h, wid, email, role="member") -> dict:
    inv = await client.post(
        f"{API}/workspaces/{wid}/invitations",
        json={"email": email, "role": role},
        headers=owner_h,
    )
    member_h = await register_and_login(client, email)
    await client.post(
        f"{API}/invitations/accept", json={"token": inv.json()["token"]}, headers=member_h
    )
    return member_h


async def test_audit_records_actions(client: AsyncClient, overrides: None) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)

    files = {"file": ("notes.txt", b"content body for ingestion", "text/plain")}
    await client.post(f"{API}/workspaces/{wid}/documents", files=files, headers=owner)
    await client.post(
        f"{API}/workspaces/{wid}/invitations",
        json={"email": "invitee@example.com", "role": "member"},
        headers=owner,
    )

    logs = await client.get(f"{API}/workspaces/{wid}/audit-logs", headers=owner)
    assert logs.status_code == 200
    actions = {entry["action"] for entry in logs.json()}
    assert "document.upload" in actions
    assert "member.invited" in actions
    # Actor email is resolved for display.
    assert any(e["actor_email"] == "owner@example.com" for e in logs.json())


async def test_audit_requires_admin(client: AsyncClient, overrides: None) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)
    member = await _add_member(client, owner, wid, "member@example.com")
    outsider = await register_and_login(client, "outsider@example.com")

    # A plain member is forbidden (403); a non-member gets 404.
    assert (
        await client.get(f"{API}/workspaces/{wid}/audit-logs", headers=member)
    ).status_code == 403
    assert (
        await client.get(f"{API}/workspaces/{wid}/audit-logs", headers=outsider)
    ).status_code == 404
