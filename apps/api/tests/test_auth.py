"""Auth flow tests."""

from __future__ import annotations

from httpx import AsyncClient

API = "/api/v1"


async def test_register_login_me(client: AsyncClient) -> None:
    # register
    r = await client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "password123", "full_name": "A"},
    )
    assert r.status_code == 201
    assert r.json()["email"] == "a@example.com"
    assert "hashed_password" not in r.json()

    # duplicate email
    dup = await client.post(
        f"{API}/auth/register",
        json={"email": "a@example.com", "password": "password123"},
    )
    assert dup.status_code == 409

    # login
    login = await client.post(
        f"{API}/auth/login", json={"email": "a@example.com", "password": "password123"}
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    # me
    me = await client.get(
        f"{API}/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "a@example.com"


async def test_login_wrong_password(client: AsyncClient) -> None:
    await client.post(
        f"{API}/auth/register",
        json={"email": "b@example.com", "password": "password123"},
    )
    bad = await client.post(
        f"{API}/auth/login", json={"email": "b@example.com", "password": "nope"}
    )
    assert bad.status_code == 401


async def test_me_requires_token(client: AsyncClient) -> None:
    r = await client.get(f"{API}/auth/me")
    assert r.status_code == 401

    r2 = await client.get(f"{API}/auth/me", headers={"Authorization": "Bearer garbage"})
    assert r2.status_code == 401


async def test_refresh_token(client: AsyncClient) -> None:
    await client.post(
        f"{API}/auth/register",
        json={"email": "c@example.com", "password": "password123"},
    )
    login = await client.post(
        f"{API}/auth/login", json={"email": "c@example.com", "password": "password123"}
    )
    refresh = login.json()["refresh_token"]

    ok = await client.post(f"{API}/auth/refresh", json={"refresh_token": refresh})
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    # an access token is not a valid refresh token
    access = login.json()["access_token"]
    bad = await client.post(f"{API}/auth/refresh", json={"refresh_token": access})
    assert bad.status_code == 401


async def test_short_password_rejected(client: AsyncClient) -> None:
    r = await client.post(
        f"{API}/auth/register", json={"email": "d@example.com", "password": "short"}
    )
    assert r.status_code == 422
