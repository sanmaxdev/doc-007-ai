"""Workspace and membership models + role/status enums."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from doc007.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from doc007.db.models.user import User


class WorkspaceRole(enum.StrEnum):
    owner = "owner"
    admin = "admin"
    member = "member"


class MemberStatus(enum.StrEnum):
    active = "active"
    invited = "invited"
    removed = "removed"


# native_enum=False -> stored as VARCHAR + CHECK: portable across Postgres and SQLite,
# and avoids fragile Postgres ENUM type migrations.
_role_enum = Enum(WorkspaceRole, native_enum=False, length=20, name="workspace_role")
_status_enum = Enum(MemberStatus, native_enum=False, length=20, name="member_status")


class Workspace(Base, TimestampMixin):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    storage_used_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    monthly_question_limit: Mapped[int | None] = mapped_column(Integer)

    members: Mapped[list[WorkspaceMember]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Workspace {self.slug}>"


class WorkspaceMember(Base, TimestampMixin):
    __tablename__ = "workspace_members"
    __table_args__ = (
        UniqueConstraint("workspace_id", "user_id", name="uq_workspace_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[WorkspaceRole] = mapped_column(
        _role_enum, default=WorkspaceRole.member, nullable=False
    )
    status: Mapped[MemberStatus] = mapped_column(
        _status_enum, default=MemberStatus.active, nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships", foreign_keys=[user_id])

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Member ws={self.workspace_id} user={self.user_id} role={self.role}>"
