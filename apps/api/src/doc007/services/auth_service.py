"""Authentication / user business logic."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.exceptions import ConflictError, UnauthorizedError
from doc007.core.security import hash_password, verify_password
from doc007.db.models.user import User


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await db.get(User, user_id)


async def register_user(
    db: AsyncSession, *, email: str, password: str, full_name: str | None = None
) -> User:
    email = email.strip().lower()
    if await get_user_by_email(db, email):
        raise ConflictError("An account with this email already exists.")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate(db: AsyncSession, *, email: str, password: str) -> User:
    user = await get_user_by_email(db, email.strip().lower())
    if user is None or not verify_password(password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password.")
    if not user.is_active:
        raise UnauthorizedError("This account is disabled.")

    user.last_login_at = datetime.now(UTC)
    await db.commit()
    return user
