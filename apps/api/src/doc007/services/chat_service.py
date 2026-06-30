"""Chat business logic: conversations + the ask orchestration."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from doc007.core.config import settings
from doc007.core.exceptions import NotFoundError, ValidationError
from doc007.db.models.conversation import Citation, Conversation, Message, MessageRole
from doc007.db.models.feedback import Feedback, FeedbackRating
from doc007.db.models.usage import UsageEventType
from doc007.db.models.workspace import Workspace
from doc007.providers.base import ChatMessage, EmbeddingProvider, LLMProvider
from doc007.rag.answer import AnswerResult, build_citations, coverage, generate_answer
from doc007.rag.answer import Citation as AnswerCitation
from doc007.rag.prompt import NOT_FOUND, build_messages
from doc007.rag.retrieval import RetrievedChunk, passes_guardrail, retrieve
from doc007.rag.vector_store import VectorStore
from doc007.services import usage_service

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
    source: str = "app",
) -> tuple[Conversation, Message, AnswerResult]:
    # Enforce the workspace's monthly question quota before spending any tokens.
    workspace = await db.get(Workspace, workspace_id)
    if workspace is not None:
        await usage_service.check_question_quota(db, workspace)

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

    assistant = await _persist_turn(
        db,
        conversation=conv,
        question=question,
        answer=result.answer,
        retrieved=result.retrieved,
        citations=result.citations,
        model=result.model,
        tokens_in=result.tokens_prompt,
        tokens_out=result.tokens_completion,
        latency_ms=result.latency_ms,
    )
    await usage_service.record(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        event_type=UsageEventType.question,
        source=source,
        tokens_in=result.tokens_prompt,
        tokens_out=result.tokens_completion,
    )
    return conv, assistant, result


async def _persist_turn(
    db: AsyncSession,
    *,
    conversation: Conversation,
    question: str,
    answer: str,
    retrieved: list[RetrievedChunk],
    citations: list[AnswerCitation],
    model: str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: int,
) -> Message:
    db.add(Message(conversation_id=conversation.id, role=MessageRole.user, content=question))
    assistant = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content=answer,
        model=model or None,
        tokens_prompt=tokens_in,
        tokens_completion=tokens_out,
        latency_ms=latency_ms,
        retrieval={
            "retrieved": [
                {
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "page_number": c.page_number,
                    "score": c.score,
                }
                for c in retrieved
            ]
        },
    )
    db.add(assistant)
    await db.flush()
    for c in citations:
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
    return assistant


async def stream_ask(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID,
    conversation: Conversation,
    question: str,
    embedder: EmbeddingProvider,
    llm: LLMProvider,
    vector_store: VectorStore,
    document_ids: list[uuid.UUID] | None = None,
    source: str = "app",
) -> AsyncIterator[dict]:
    """Yield token/done events while streaming an answer.

    The caller resolves the conversation and checks the quota first (so those
    can return normal HTTP errors); this generator runs retrieval, streams the
    answer, then persists the turn and records usage.
    """
    history = await _history(db, conversation.id)
    chunks = await retrieve(
        db,
        workspace_id=workspace_id,
        query=question,
        embedder=embedder,
        vector_store=vector_store,
        top_k=settings.retrieval_top_k,
        document_ids=document_ids,
    )

    if not passes_guardrail(chunks):
        yield {"type": "token", "text": NOT_FOUND}
        message = await _persist_turn(
            db,
            conversation=conversation,
            question=question,
            answer=NOT_FOUND,
            retrieved=chunks,
            citations=[],
            model="",
            tokens_in=0,
            tokens_out=0,
            latency_ms=0,
        )
        await usage_service.record(
            db,
            workspace_id=workspace_id,
            user_id=user_id,
            event_type=UsageEventType.question,
            source=source,
        )
        yield {
            "type": "done",
            "conversation_id": str(conversation.id),
            "message_id": str(message.id),
            "citations": [],
            "coverage": "none",
            "not_found": True,
        }
        return

    messages = build_messages(question, chunks, history)
    parts: list[str] = []
    started = time.monotonic()
    async for token in llm.stream(messages):
        parts.append(token)
        yield {"type": "token", "text": token}

    answer = "".join(parts).strip()
    latency_ms = int((time.monotonic() - started) * 1000)
    citations = build_citations(answer, chunks)
    tokens_in = sum(len(m.content.split()) for m in messages)
    tokens_out = len(answer.split())

    message = await _persist_turn(
        db,
        conversation=conversation,
        question=question,
        answer=answer,
        retrieved=chunks,
        citations=citations,
        model=llm.name,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
    )
    await usage_service.record(
        db,
        workspace_id=workspace_id,
        user_id=user_id,
        event_type=UsageEventType.question,
        source=source,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
    )
    yield {
        "type": "done",
        "conversation_id": str(conversation.id),
        "message_id": str(message.id),
        "citations": [
            {
                "index": c.index,
                "document_id": c.document_id,
                "document_filename": c.document_filename,
                "page_number": c.page_number,
                "snippet": c.snippet,
                "score": c.score,
            }
            for c in citations
        ],
        "coverage": coverage(chunks, len(citations)),
        "not_found": answer.lower().startswith("i couldn't find"),
    }
