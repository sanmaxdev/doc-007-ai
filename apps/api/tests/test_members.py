"""Invitations, RBAC enforcement, and member management."""

from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import register_and_login

API = "/api/v1"


async def _workspace(client: AsyncClient, headers: dict, name: str = "Acme") -> str:
    resp = await client.post(f"{API}/workspaces", json={"name": name}, headers=headers)
    return resp.json()["id"]


async def _invite(client, owner_h, wid, email, role="member") -> str:
    resp = await client.post(
        f"{API}/workspaces/{wid}/invitations",
        json={"email": email, "role": role},
        headers=owner_h,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["token"]


async def _add_member(client, owner_h, wid, email, role="member") -> dict:
    token = await _invite(client, owner_h, wid, email, role)
    member_h = await register_and_login(client, email)
    accepted = await client.post(
        f"{API}/invitations/accept", json={"token": token}, headers=member_h
    )
    assert accepted.status_code == 200, accepted.text
    return member_h


async def _member_id(client, owner_h, wid, email) -> str:
    members = await client.get(f"{API}/workspaces/{wid}/members", headers=owner_h)
    return next(m["user_id"] for m in members.json() if m["email"] == email)


async def test_invite_and_accept_flow(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)

    bob = await _add_member(client, owner, wid, "bob@example.com")

    members = await client.get(f"{API}/workspaces/{wid}/members", headers=owner)
    assert len(members.json()) == 2
    # Bob can now reach the workspace he joined.
    assert (await client.get(f"{API}/workspaces/{wid}", headers=bob)).status_code == 200
    # The invitation is consumed (no longer pending).
    pending = await client.get(f"{API}/workspaces/{wid}/invitations", headers=owner)
    assert pending.json() == []


async def test_accept_bad_token_and_wrong_email(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)
    token = await _invite(client, owner, wid, "invited@example.com")

    stranger = await register_and_login(client, "stranger@example.com")
    # Bad token -> 404
    assert (
        await client.post(f"{API}/invitations/accept", json={"token": "nope"}, headers=stranger)
    ).status_code == 404
    # Right token, wrong email -> 403
    wrong = await client.post(
        f"{API}/invitations/accept", json={"token": token}, headers=stranger
    )
    assert wrong.status_code == 403


async def test_member_cannot_invite(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)
    member = await _add_member(client, owner, wid, "member@example.com")

    # A plain member lacks the admin role -> 403 (not 404; they ARE a member).
    resp = await client.post(
        f"{API}/workspaces/{wid}/invitations",
        json={"email": "another@example.com", "role": "member"},
        headers=member,
    )
    assert resp.status_code == 403


async def test_role_change_requires_owner(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)
    await _add_member(client, owner, wid, "bob@example.com")
    admin = await _add_member(client, owner, wid, "admin@example.com", role="admin")
    bob_id = await _member_id(client, owner, wid, "bob@example.com")

    # Owner promotes Bob to admin.
    promo = await client.patch(
        f"{API}/workspaces/{wid}/members/{bob_id}/role",
        json={"role": "admin"},
        headers=owner,
    )
    assert promo.status_code == 200 and promo.json()["role"] == "admin"

    # An admin cannot change roles (owner-only).
    assert (
        await client.patch(
            f"{API}/workspaces/{wid}/members/{bob_id}/role",
            json={"role": "member"},
            headers=admin,
        )
    ).status_code == 403

    # The owner's own role cannot be changed.
    owner_id = await _member_id(client, owner, wid, "owner@example.com")
    assert (
        await client.patch(
            f"{API}/workspaces/{wid}/members/{owner_id}/role",
            json={"role": "admin"},
            headers=owner,
        )
    ).status_code == 403


async def test_remove_member_rules(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    wid = await _workspace(client, owner)
    await _add_member(client, owner, wid, "member@example.com")
    admin = await _add_member(client, owner, wid, "admin@example.com", role="admin")

    member_id = await _member_id(client, owner, wid, "member@example.com")
    admin_id = await _member_id(client, owner, wid, "admin@example.com")
    owner_id = await _member_id(client, owner, wid, "owner@example.com")

    # Admin can remove a plain member.
    assert (
        await client.delete(f"{API}/workspaces/{wid}/members/{member_id}", headers=admin)
    ).status_code == 204

    # The owner can never be removed.
    assert (
        await client.delete(f"{API}/workspaces/{wid}/members/{owner_id}", headers=admin)
    ).status_code == 403

    # An admin cannot remove another admin: re-add one and have the first admin try.
    await _add_member(client, owner, wid, "admin2@example.com", role="admin")
    admin2_id = await _member_id(client, owner, wid, "admin2@example.com")
    assert (
        await client.delete(f"{API}/workspaces/{wid}/members/{admin2_id}", headers=admin)
    ).status_code == 403
    # But the owner can.
    assert (
        await client.delete(f"{API}/workspaces/{wid}/members/{admin_id}", headers=owner)
    ).status_code == 204


async def test_invitation_isolation(client: AsyncClient) -> None:
    owner = await register_and_login(client, "owner@example.com")
    outsider = await register_and_login(client, "outsider@example.com")
    wid = await _workspace(client, owner)

    # A non-member cannot list or create invitations -> 404 (existence hidden).
    assert (
        await client.get(f"{API}/workspaces/{wid}/invitations", headers=outsider)
    ).status_code == 404
    assert (
        await client.post(
            f"{API}/workspaces/{wid}/invitations",
            json={"email": "x@example.com", "role": "member"},
            headers=outsider,
        )
    ).status_code == 404
