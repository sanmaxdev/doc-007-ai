"""User model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doc007.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from doc007.db.models.workspace import WorkspaceMember


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="user",
        foreign_keys="WorkspaceMember.user_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"
