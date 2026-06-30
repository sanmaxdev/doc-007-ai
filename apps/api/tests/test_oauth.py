"""OAuth (SSO) sign-in: providers, authorize guard, callback creates/links user."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.services import auth_service, oauth_service
from doc007.services.oauth_service import OAuthUser

API = "/api/v1"


async def test_providers_empty_by_default(client: AsyncClient) -> None:
    # No client ids/secrets configured in tests -> no SSO providers.
    r = await client.get(f"{API}/auth/oauth/providers")
    assert r.status_code == 200
    assert r.json()["providers"] == []


async def test_authorize_rejects_unconfigured_provider(client: AsyncClient) -> None:
    r = await client.post(
        f"{API}/auth/oauth/authorize",
        json={"provider": "google", "redirect_uri": "http://localhost:3000/oauth/google/callback"},
    )
    assert r.status_code == 404


async def test_callback_creates_then_links(client: AsyncClient, monkeypatch) -> None:
    async def fake_exchange(provider: str, code: str, redirect_uri: str) -> OAuthUser:
        return OAuthUser(
            email="sso@example.com", full_name="SSO User", provider="google", subject="123"
        )

    monkeypatch.setattr(oauth_service, "exchange_code", fake_exchange)

    r = await client.post(
        f"{API}/auth/oauth/callback",
        json={"provider": "google", "code": "abc", "redirect_uri": "http://x/cb"},
    )
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    me = await client.get(
        f"{API}/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.json()["email"] == "sso@example.com"
    assert me.json()["is_verified"] is True

    # Signing in again with the same email reuses the account.
    again = await client.post(
        f"{API}/auth/oauth/callback",
        json={"provider": "google", "code": "def", "redirect_uri": "http://x/cb"},
    )
    assert again.status_code == 200


async def test_oauth_links_existing_password_account(session: AsyncSession) -> None:
    existing = await auth_service.register_user(
        session, email="dual@example.com", password="password123"
    )
    linked = await auth_service.get_or_create_oauth_user(
        session, email="dual@example.com", full_name="Dual"
    )
    assert linked.id == existing.id

    fresh = await auth_service.get_or_create_oauth_user(session, email="brandnew@example.com")
    assert fresh.is_verified is True
    assert fresh.id != existing.id
