"""Answer feedback model (helpful / not helpful per message, per user)."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum, ForeignKey, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from doc007.db.base import Base, TimestampMixin


class FeedbackRating(enum.StrEnum):
    helpful = "helpful"
    not_helpful = "not_helpful"


_rating_enum = Enum(FeedbackRating, native_enum=False, length=20, name="feedback_rating")


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", name="uq_feedback_message_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    message_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[FeedbackRating] = mapped_column(_rating_enum, nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Feedback {self.rating} msg={self.message_id}>"
