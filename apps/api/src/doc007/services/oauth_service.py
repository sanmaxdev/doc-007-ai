"""OAuth (social SSO) for Google and GitHub.

A provider is enabled only when its client id and secret are configured, so the
feature degrades gracefully to "no SSO buttons" when nothing is set. The login
flow is: authorize_url -> provider consent -> callback code -> exchange_code,
which returns a verified email used to find or create the local user.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from doc007.core.config import settings
from doc007.core.exceptions import NotFoundError, UnauthorizedError


@dataclass
class _ProviderCfg:
    name: str
    client_id: str
    client_secret: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str


@dataclass
class OAuthUser:
    email: str
    full_name: str | None
    provider: str
    subject: str | None


def _configs() -> dict[str, _ProviderCfg]:
    cfgs: dict[str, _ProviderCfg] = {}
    if settings.google_client_id and settings.google_client_secret:
        cfgs["google"] = _ProviderCfg(
            name="google",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
            token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
            scope="openid email profile",
        )
    if settings.github_client_id and settings.github_client_secret:
        cfgs["github"] = _ProviderCfg(
            name="github",
            client_id=settings.github_client_id,
            client_secret=settings.github_client_secret,
            authorize_url="https://github.com/login/oauth/authorize",
            token_url="https://github.com/login/oauth/access_token",
            userinfo_url="https://api.github.com/user",
            scope="read:user user:email",
        )
    return cfgs


def enabled_providers() -> list[str]:
    return list(_configs().keys())


def _require(provider: str) -> _ProviderCfg:
    cfg = _configs().get(provider)
    if cfg is None:
        raise NotFoundError("Unknown or disabled SSO provider.")
    return cfg


def authorize_url(provider: str, redirect_uri: str, state: str) -> str:
    cfg = _require(provider)
    params = {
        "client_id": cfg.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": cfg.scope,
        "state": state,
    }
    return f"{cfg.authorize_url}?{urlencode(params)}"


async def exchange_code(provider: str, code: str, redirect_uri: str) -> OAuthUser:
    cfg = _require(provider)
    async with httpx.AsyncClient(timeout=15) as client:
        token_resp = await client.post(
            cfg.token_url,
            data={
                "client_id": cfg.client_id,
                "client_secret": cfg.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        access_token = token_resp.json().get("access_token") if token_resp.is_success else None
        if not access_token:
            raise UnauthorizedError("Could not complete sign-in with the provider.")

        auth_headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        info_resp = await client.get(cfg.userinfo_url, headers=auth_headers)
        info = info_resp.json() if info_resp.is_success else {}

        if provider == "google":
            email = info.get("email")
            verified = bool(info.get("email_verified"))
            name = info.get("name")
            subject = info.get("sub")
        else:  # github
            email = info.get("email")
            name = info.get("name") or info.get("login")
            subject = str(info.get("id")) if info.get("id") is not None else None
            verified = True
            if not email:
                emails_resp = await client.get(
                    "https://api.github.com/user/emails", headers=auth_headers
                )
                emails = emails_resp.json() if emails_resp.is_success else []
                primary = next(
                    (e for e in emails if e.get("primary") and e.get("verified")), None
                )
                email = primary.get("email") if primary else None

        if not email or not verified:
            raise UnauthorizedError("The provider did not return a verified email address.")

        return OAuthUser(
            email=email.strip().lower(), full_name=name, provider=provider, subject=subject
        )
