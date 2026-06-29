"""Workspace creation, membership, and tenant isolation tests."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import register_and_login

API = "/api/v1"


async def test_create_list_get_workspace(client: AsyncClient) -> None:
    h = await register_and_login(client, "owner@example.com")

    created = await client.post(f"{API}/workspaces", json={"name": "Acme Inc"}, headers=h)
    assert created.status_code == 201
    ws = created.json()
    assert ws["role"] == "owner"
    assert ws["slug"].startswith("acme-inc-")

    listed = await client.get(f"{API}/workspaces", headers=h)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["id"] == ws["id"]

    detail = await client.get(f"{API}/workspaces/{ws['id']}", headers=h)
    assert detail.status_code == 200
    assert detail.json()["role"] == "owner"

    members = await client.get(f"{API}/workspaces/{ws['id']}/members", headers=h)
    assert members.status_code == 200
    assert len(members.json()) == 1
    assert members.json()[0]["email"] == "owner@example.com"
    assert members.json()[0]["role"] == "owner"


async def test_workspace_isolation(client: AsyncClient) -> None:
    """The core security guarantee: a user cannot touch another tenant's workspace."""
    alice = await register_and_login(client, "alice@example.com")
    bob = await register_and_login(client, "bob@example.com")

    created = await client.post(f"{API}/workspaces", json={"name": "Alice Co"}, headers=alice)
    ws_id = created.json()["id"]

    # Bob's list is empty
    bob_list = await client.get(f"{API}/workspaces", headers=bob)
    assert bob_list.json() == []

    # Bob cannot read Alice's workspace — 404, not 403, so existence isn't leaked
    assert (await client.get(f"{API}/workspaces/{ws_id}", headers=bob)).status_code == 404

    # Bob cannot list its members
    assert (
        await client.get(f"{API}/workspaces/{ws_id}/members", headers=bob)
    ).status_code == 404

    # Unauthenticated access is rejected
    assert (await client.get(f"{API}/workspaces/{ws_id}")).status_code == 401


async def test_create_workspace_requires_auth(client: AsyncClient) -> None:
    r = await client.post(f"{API}/workspaces", json={"name": "No Auth"})
    assert r.status_code == 401
