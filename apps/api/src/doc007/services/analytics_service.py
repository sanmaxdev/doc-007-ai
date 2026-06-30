"""Workspace analytics: answer rate, knowledge gaps, top cited docs, feedback.

Read-only aggregation over messages, citations, and feedback. All scoped by
workspace via the conversation join.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.db.models.conversation import Citation, Conversation, Message, MessageRole
from doc007.db.models.feedback import Feedback, FeedbackRating
from doc007.rag.prompt import NOT_FOUND

_RECENT_LIMIT = 10


async def workspace_analytics(db: AsyncSession, workspace_id: uuid.UUID) -> dict:
    # Pull recent messages and pair each question with its answer in Python.
    # (now() is stable within a transaction, so user/assistant rows can share a
    # timestamp; the role tiebreaker keeps the question before its answer.)
    rows = await db.execute(
        select(
            Message.role,
            Message.content,
            Message.created_at,
            Message.conversation_id,
        )
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.workspace_id == workspace_id)
    )
    messages = list(rows.all())
    messages.sort(
        key=lambda r: (
            str(r.conversation_id),
            r.created_at,
            0 if r.role == MessageRole.user else 1,
        )
    )

    pairs: list[tuple[str, bool, datetime]] = []  # (question, answered, created_at)
    pending: dict[uuid.UUID, tuple[str, datetime]] = {}
    for r in messages:
        if r.role == MessageRole.user:
            pending[r.conversation_id] = (r.content, r.created_at)
        elif r.role == MessageRole.assistant:
            q = pending.pop(r.conversation_id, None)
            if q is not None:
                answered = r.content.strip() != NOT_FOUND
                pairs.append((q[0], answered, q[1]))

    total = len(pairs)
    unanswered = sum(1 for _, answered, _ in pairs if not answered)
    answered = total - unanswered
    answer_rate = round(answered / total, 4) if total else 0.0

    by_recent = sorted(pairs, key=lambda p: p[2], reverse=True)
    recent_questions = [
        {"question": q, "answered": a, "created_at": ts} for q, a, ts in by_recent[:_RECENT_LIMIT]
    ]
    unanswered_questions = [
        {"question": q, "answered": a, "created_at": ts}
        for q, a, ts in by_recent
        if not a
    ][:_RECENT_LIMIT]

    # Top cited documents.
    top = await db.execute(
        select(
            Citation.document_id,
            Citation.document_filename,
            func.count().label("n"),
        )
        .join(Message, Message.id == Citation.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.workspace_id == workspace_id)
        .group_by(Citation.document_id, Citation.document_filename)
        .order_by(func.count().desc())
        .limit(5)
    )
    top_documents = [
        {"document_id": did, "filename": fname, "citations": int(n)}
        for did, fname, n in top.all()
    ]

    # Feedback tallies.
    fb = await db.execute(
        select(Feedback.rating, func.count())
        .join(Message, Message.id == Feedback.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Conversation.workspace_id == workspace_id)
        .group_by(Feedback.rating)
    )
    fb_map = {str(rating): int(n) for rating, n in fb.all()}

    return {
        "total_questions": total,
        "answered": answered,
        "unanswered": unanswered,
        "answer_rate": answer_rate,
        "feedback_helpful": fb_map.get(str(FeedbackRating.helpful), 0),
        "feedback_not_helpful": fb_map.get(str(FeedbackRating.not_helpful), 0),
        "top_documents": top_documents,
        "recent_questions": recent_questions,
        "unanswered_questions": unanswered_questions,
    }
