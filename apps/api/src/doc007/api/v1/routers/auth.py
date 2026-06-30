"""Auth endpoints: register, login, refresh, logout, me."""

from __future__ import annotations

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core import token_blocklist
from doc007.core.deps import enforce_auth_rate_limit, get_access_payload, get_current_user
from doc007.core.exceptions import UnauthorizedError
from doc007.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    token_ttl_seconds,
)
from doc007.db.base import get_db
from doc007.db.models.user import User
from doc007.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    OAuthAuthorizeRequest,
    OAuthAuthorizeResponse,
    OAuthCallbackRequest,
    OAuthProvidersOut,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from doc007.services import auth_service, oauth_service

router = APIRouter()


def _tokens_for(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    return await auth_service.register_user(
        db, email=data.email, password=data.password, full_name=data.full_name
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await auth_service.authenticate(db, email=data.email, password=data.password)
    return _tokens_for(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    dependencies=[Depends(enforce_auth_rate_limit)],
)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token.")
    if await token_blocklist.is_revoked(str(payload.get("jti", ""))):
        raise UnauthorizedError("Refresh token has been revoked.")
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid refresh token.") from None

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    # Rotate: the presented refresh token is single-use and is revoked here.
    await token_blocklist.revoke(str(payload.get("jti", "")), token_ttl_seconds(payload))
    return _tokens_for(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    data: LogoutRequest | None = None,
    payload: dict[str, Any] = Depends(get_access_payload),
) -> dict:
    # Revoke the current access token, and the refresh token if the client sends it.
    await token_blocklist.revoke(str(payload.get("jti", "")), token_ttl_seconds(payload))
    if data and data.refresh_token:
        rp = decode_token(data.refresh_token)
        if rp and rp.get("type") == "refresh":
            await token_blocklist.revoke(str(rp.get("jti", "")), token_ttl_seconds(rp))
    return {"detail": "Logged out."}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


# ---- OAuth / SSO ---------------------------------------------------------


@router.get("/oauth/providers", response_model=OAuthProvidersOut)
async def oauth_providers() -> OAuthProvidersOut:
    return OAuthProvidersOut(providers=oauth_service.enabled_providers())


@router.post("/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def oauth_authorize(data: OAuthAuthorizeRequest) -> OAuthAuthorizeResponse:
    state = secrets.token_urlsafe(16)
    url = oauth_service.authorize_url(data.provider, data.redirect_uri, state)
    return OAuthAuthorizeResponse(authorize_url=url, state=state)


@router.post("/oauth/callback", response_model=TokenResponse)
async def oauth_callback(
    data: OAuthCallbackRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    profile = await oauth_service.exchange_code(data.provider, data.code, data.redirect_uri)
    user = await auth_service.get_or_create_oauth_user(
        db, email=profile.email, full_name=profile.full_name
    )
    return _tokens_for(user)
