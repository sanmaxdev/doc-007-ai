"""Chat endpoints (workspace-scoped): conversations + ask."""

from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import (
    get_embedder_dep,
    get_llm_dep,
    get_membership,
    get_vector_store_dep,
)
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
from doc007.db.models.audit import AuditAction
from doc007.db.models.conversation import Message
from doc007.db.models.workspace import WorkspaceMember
from doc007.providers.base import EmbeddingProvider, LLMProvider
from doc007.rag.answer import Citation as AnswerCitation
from doc007.rag.vector_store import VectorStore
from doc007.schemas.chat import (
    AskRequest,
    AskResponse,
    CitationOut,
    ConversationDetail,
    ConversationOut,
    FeedbackOut,
    FeedbackRequest,
    MessageOut,
)
from doc007.services import audit_service, chat_service, usage_service, workspace_service

router = APIRouter()


def _citation_from_answer(c: AnswerCitation) -> CitationOut:
    return CitationOut(
        index=c.index,
        document_id=uuid.UUID(c.document_id),
        document_filename=c.document_filename,
        page_number=c.page_number,
        snippet=c.snippet,
        score=c.score,
    )


def _message_out(m: Message) -> MessageOut:
    return MessageOut(
        id=m.id,
        role=str(m.role),
        content=m.content,
        created_at=m.created_at,
        citations=[
            CitationOut(
                index=c.rank + 1,
                document_id=c.document_id,
                document_filename=c.document_filename,
                page_number=c.page_number,
                snippet=c.snippet,
                score=c.score,
            )
            for c in m.citations
        ],
    )


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    convs = await chat_service.list_conversations(
        db, membership.workspace_id, membership.user_id, limit=limit, offset=offset
    )
    return [ConversationOut.model_validate(c) for c in convs]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetail:
    conv = await chat_service.get_conversation(
        db, membership.workspace_id, conversation_id, membership.user_id
    )
    if conv is None:
        raise NotFoundError("Conversation not found.")
    messages = await chat_service.get_messages(db, conversation_id)
    return ConversationDetail(
        conversation=ConversationOut.model_validate(conv),
        messages=[_message_out(m) for m in messages],
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> Response:
    conv = await chat_service.get_conversation(
        db, membership.workspace_id, conversation_id, membership.user_id
    )
    if conv is None:
        raise NotFoundError("Conversation not found.")
    await chat_service.delete_conversation(db, conv)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/ask", response_model=AskResponse)
async def ask(
    payload: AskRequest,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder_dep),
    llm: LLMProvider = Depends(get_llm_dep),
    vector_store: VectorStore = Depends(get_vector_store_dep),
) -> AskResponse:
    conv, message, result = await chat_service.ask(
        db,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        question=payload.question,
        conversation_id=payload.conversation_id,
        document_ids=payload.document_ids,
        embedder=embedder,
        llm=llm,
        vector_store=vector_store,
    )
    await audit_service.record(
        db,
        workspace_id=membership.workspace_id,
        actor_id=membership.user_id,
        action=AuditAction.question_asked,
        target_type="conversation",
        target_id=conv.id,
    )
    return AskResponse(
        conversation_id=conv.id,
        message_id=message.id,
        answer=result.answer,
        citations=[_citation_from_answer(c) for c in result.citations],
        coverage=result.coverage,
        not_found=result.not_found,
    )


@router.post("/ask/stream")
async def ask_stream(
    payload: AskRequest,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
    embedder: EmbeddingProvider = Depends(get_embedder_dep),
    llm: LLMProvider = Depends(get_llm_dep),
    vector_store: VectorStore = Depends(get_vector_store_dep),
) -> StreamingResponse:
    # Validate up front so quota/not-found errors return real HTTP status codes
    # before the stream starts.
    workspace = await workspace_service.get_workspace(db, membership.workspace_id)
    if workspace is not None:
        await usage_service.check_question_quota(db, workspace)

    if payload.conversation_id is not None:
        conv = await chat_service.get_conversation(
            db, membership.workspace_id, payload.conversation_id, membership.user_id
        )
        if conv is None:
            raise NotFoundError("Conversation not found.")
    else:
        conv = await chat_service.create_conversation(
            db,
            workspace_id=membership.workspace_id,
            user_id=membership.user_id,
            title=payload.question[:80],
        )

    async def event_stream():
        try:
            async for event in chat_service.stream_ask(
                db,
                workspace_id=membership.workspace_id,
                user_id=membership.user_id,
                conversation=conv,
                question=payload.question,
                embedder=embedder,
                llm=llm,
                vector_store=vector_store,
                document_ids=payload.document_ids,
            ):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as exc:  # noqa: BLE001
            yield f"data: {json.dumps({'type': 'error', 'detail': str(exc)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/messages/{message_id}/feedback", response_model=FeedbackOut)
async def submit_feedback(
    message_id: uuid.UUID,
    payload: FeedbackRequest,
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> FeedbackOut:
    feedback = await chat_service.submit_feedback(
        db,
        workspace_id=membership.workspace_id,
        user_id=membership.user_id,
        message_id=message_id,
        rating=payload.rating,
        comment=payload.comment,
    )
    return FeedbackOut.model_validate(feedback)
