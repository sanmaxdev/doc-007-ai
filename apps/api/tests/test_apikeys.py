"""API key management: create (shown once), list, revoke, RBAC."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import register_and_login

API = "/api/v1"


async def _ws(client: AsyncClient, h: dict, name: str = "Acme") -> str:
    return (await client.post(f"{API}/workspaces", json={"name": name}, headers=h)).json()["id"]


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


async def test_create_list_revoke(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _ws(client, owner)

    created = await client.post(
        f"{API}/workspaces/{wid}/api-keys", json={"name": "CI key"}, headers=owner
    )
    assert created.status_code == 201, created.text
    body = created.json()
    raw = body["key"]
    assert raw.startswith("doc7_")  # raw key returned once
    assert body["api_key"]["key_prefix"] == raw[:12]
    key_id = body["api_key"]["id"]

    listed = await client.get(f"{API}/workspaces/{wid}/api-keys", headers=owner)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert "key" not in listed.json()[0]  # raw key never returned again
    assert listed.json()[0]["revoked_at"] is None

    revoked = await client.delete(f"{API}/workspaces/{wid}/api-keys/{key_id}", headers=owner)
    assert revoked.status_code == 204
    after = await client.get(f"{API}/workspaces/{wid}/api-keys", headers=owner)
    assert after.json()[0]["revoked_at"] is not None


async def test_api_key_rbac(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _ws(client, owner)
    member = await _add_member(client, owner, wid, "member@example.com")
    outsider = await register_and_login(client, "outsider@example.com")

    # A plain member is forbidden (403); a non-member gets 404.
    assert (
        await client.post(
            f"{API}/workspaces/{wid}/api-keys", json={"name": "x"}, headers=member
        )
    ).status_code == 403
    assert (
        await client.post(
            f"{API}/workspaces/{wid}/api-keys", json={"name": "x"}, headers=outsider
        )
    ).status_code == 404
