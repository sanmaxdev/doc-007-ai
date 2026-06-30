"""Workspace invitation model."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from doc007.db.base import Base, TimestampMixin
from doc007.db.models.workspace import WorkspaceRole


class InvitationStatus(enum.StrEnum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


_status_enum = Enum(InvitationStatus, native_enum=False, length=20, name="invitation_status")
_role_enum = Enum(WorkspaceRole, native_enum=False, length=20, name="invitation_role")


class Invitation(Base, TimestampMixin):
    __tablename__ = "invitations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[WorkspaceRole] = mapped_column(
        _role_enum, default=WorkspaceRole.member, nullable=False
    )
    # Only the SHA-256 hash of the token is stored; the raw token is shown once.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        _status_enum, default=InvitationStatus.pending, nullable=False
    )
    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Invitation {self.email} ws={self.workspace_id} status={self.status}>"
