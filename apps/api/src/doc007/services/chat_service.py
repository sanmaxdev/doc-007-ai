"""Chat business logic: conversations + the ask orchestration."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from doc007.core.exceptions import NotFoundError, ValidationError
from doc007.db.models.conversation import Citation, Conversation, Message, MessageRole
from doc007.db.models.feedback import Feedback, FeedbackRating
from doc007.providers.base import ChatMessage, EmbeddingProvider, LLMProvider
from doc007.rag.answer import AnswerResult, generate_answer
from doc007.rag.vector_store import VectorStore

_HISTORY_LIMIT = 6


async def create_conversation(
    db: AsyncSession, *, workspace_id: uuid.UUID, user_id: uuid.UUID, title: str | None = None
) -> Conversation:
    conv = Conversation(workspace_id=workspace_id, user_id=user_id, title=title)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def list_conversations(
    db: AsyncSession, workspace_id: uuid.UUID, user_id: uuid.UUID
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.workspace_id == workspace_id, Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    return list(result.scalars().all())


async def get_conversation(
    db: AsyncSession, workspace_id: uuid.UUID, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_messages(db: AsyncSession, conversation_id: uuid.UUID) -> list[Message]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .options(selectinload(Message.citations))
        .order_by(Message.created_at.asc())
    )
    return list(result.scalars().all())


async def delete_conversation(db: AsyncSession, conversation: Conversation) -> None:
    await db.delete(conversation)
    await db.commit()


async def submit_feedback(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    message_id: uuid.UUID,
    rating: FeedbackRating,
    comment: str | None = None,
) -> Feedback:
    result = await db.execute(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.id == message_id,
            Conversation.workspace_id == workspace_id,
            Conversation.user_id == user_id,
        )
    )
    message = result.scalar_one_or_none()
    if message is None:
        raise NotFoundError("Message not found.")
    if message.role != MessageRole.assistant:
        raise ValidationError("Feedback can only be given on assistant answers.")

    existing = await db.execute(
        select(Feedback).where(
            Feedback.message_id == message_id, Feedback.user_id == user_id
        )
    )
    feedback = existing.scalar_one_or_none()
    if feedback is None:
        feedback = Feedback(
            message_id=message_id, user_id=user_id, rating=rating, comment=comment
        )
        db.add(feedback)
    else:
        feedback.rating = rating
        feedback.comment = comment
    await db.commit()
    await db.refresh(feedback)
    return feedback


async def _history(db: AsyncSession, conversation_id: uuid.UUID) -> list[ChatMessage]:
    messages = await get_messages(db, conversation_id)
    recent = messages[-_HISTORY_LIMIT:]
    return [
        ChatMessage(role=m.role.value, content=m.content)
        for m in recent
        if m.role in (MessageRole.user, MessageRole.assistant)
    ]


async def ask(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    question: str,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    vector_store: VectorStore,
    conversation_id: uuid.UUID | None = None,
    document_ids: list[uuid.UUID] | None = None,
) -> tuple[Conversation, Message, AnswerResult]:
    if conversation_id is not None:
        conv = await get_conversation(db, workspace_id, conversation_id, user_id)
        if conv is None:
            raise NotFoundError("Conversation not found.")
    else:
        conv = await create_conversation(
            db, workspace_id=workspace_id, user_id=user_id, title=question[:80]
        )

    history = await _history(db, conv.id)
    result = await generate_answer(
        db,
        workspace_id=workspace_id,
        question=question,
        embedder=embedder,
        llm=llm,
        vector_store=vector_store,
        history=history,
        document_ids=document_ids,
    )

    db.add(Message(conversation_id=conv.id, role=MessageRole.user, content=question))
    assistant = Message(
        conversation_id=conv.id,
        role=MessageRole.assistant,
        content=result.answer,
        model=result.model,
        tokens_prompt=result.tokens_prompt,
        tokens_completion=result.tokens_completion,
        latency_ms=result.latency_ms,
        retrieval={
            "retrieved": [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "page_number": c.page_number,
                    "score": c.score,
                }
                for c in result.retrieved
            ]
        },
    )
    db.add(assistant)
    await db.flush()

    for c in result.citations:
        db.add(
            Citation(
                message_id=assistant.id,
                document_id=uuid.UUID(c.document_id),
                chunk_id=uuid.UUID(c.chunk_id),
                document_filename=c.document_filename,
                page_number=c.page_number,
                snippet=c.snippet,
                score=c.score,
                rank=c.rank,
            )
        )

    await db.commit()
    await db.refresh(assistant)
    return conv, assistant, result
