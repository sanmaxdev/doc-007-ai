"""Auth-related request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    # Optional: pass the refresh token so it is revoked too, not just the access token.
    refresh_token: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_verified: bool
    created_at: datetime


class OAuthProvidersOut(BaseModel):
    providers: list[str]


class OAuthAuthorizeRequest(BaseModel):
    provider: str
    redirect_uri: str


class OAuthAuthorizeResponse(BaseModel):
    authorize_url: str
    state: str


class OAuthCallbackRequest(BaseModel):
    provider: str
    code: str
    redirect_uri: str
