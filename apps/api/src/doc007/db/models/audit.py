"""Audit log model.

Append-only record of security- and content-relevant actions in a workspace.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from doc007.db.base import Base


class AuditAction(enum.StrEnum):
    document_upload = "document.upload"
    document_delete = "document.delete"
    document_reprocess = "document.reprocess"
    question_asked = "question.asked"
    member_invited = "member.invited"
    member_removed = "member.removed"
    role_changed = "role.changed"
    invitation_accepted = "invitation.accepted"
    invitation_revoked = "invitation.revoked"
    workspace_updated = "workspace.updated"
    workspace_deleted = "workspace.deleted"
    tag_added = "tag.added"
    tag_removed = "tag.removed"
    apikey_created = "apikey.created"
    apikey_revoked = "apikey.revoked"


_action_enum = Enum(AuditAction, native_enum=False, length=40, name="audit_action")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL")
    )
    action: Mapped[AuditAction] = mapped_column(_action_enum, nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(40))
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<AuditLog {self.action} ws={self.workspace_id}>"
