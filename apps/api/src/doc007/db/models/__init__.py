"""SQLAlchemy ORM models.

Every model module is imported here so `Base.metadata` is fully populated
for Alembic autogenerate and for `create_all` in tests.
"""

from doc007.db.models.audit import AuditAction, AuditLog
from doc007.db.models.conversation import (
    Citation,
    Conversation,
    Message,
    MessageRole,
)
from doc007.db.models.document import Document, DocumentChunk, DocumentStatus
from doc007.db.models.feedback import Feedback, FeedbackRating
from doc007.db.models.invitation import Invitation, InvitationStatus
from doc007.db.models.tag import DocumentTag, Tag
from doc007.db.models.user import User
from doc007.db.models.workspace import (
    MemberStatus,
    Workspace,
    WorkspaceMember,
    WorkspaceRole,
)

__all__ = [
    "User",
    "Workspace",
    "WorkspaceMember",
    "WorkspaceRole",
    "MemberStatus",
    "Document",
    "DocumentChunk",
    "DocumentStatus",
    "Conversation",
    "Message",
    "MessageRole",
    "Citation",
    "Invitation",
    "InvitationStatus",
    "Tag",
    "DocumentTag",
    "AuditLog",
    "AuditAction",
    "Feedback",
    "FeedbackRating",
]
