"""Auth endpoints: register, login, refresh, logout, me."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import get_current_user
from doc007.core.exceptions import UnauthorizedError
from doc007.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
)
from doc007.db.base import get_db
from doc007.db.models.user import User
from doc007.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserOut,
)
from doc007.services import auth_service

router = APIRouter()


def _tokens_for(user: User) -> TokenResponse:
    subject = str(user.id)
    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: AsyncSession = Depends(get_db)) -> User:
    return await auth_service.register_user(
        db, email=data.email, password=data.password, full_name=data.full_name
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    user = await auth_service.authenticate(db, email=data.email, password=data.password)
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    payload = decode_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid refresh token.")
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (ValueError, TypeError):
        raise UnauthorizedError("Invalid refresh token.") from None

    user = await auth_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")
    return _tokens_for(user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(_: User = Depends(get_current_user)) -> dict:
    # Stateless JWT: the client discards its tokens. A server-side
    # revocation list can be added later if needed.
    return {"detail": "Logged out."}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user
