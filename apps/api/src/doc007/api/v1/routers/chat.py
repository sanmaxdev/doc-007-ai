"""Chat endpoints (workspace-scoped): conversations + ask."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.deps import (
    get_embedder_dep,
    get_llm_dep,
    get_membership,
    get_vector_store_dep,
)
from doc007.core.exceptions import NotFoundError
from doc007.db.base import get_db
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
    MessageOut,
)
from doc007.services import chat_service

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
    membership: WorkspaceMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    convs = await chat_service.list_conversations(
        db, membership.workspace_id, membership.user_id
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
    return AskResponse(
        conversation_id=conv.id,
        message_id=message.id,
        answer=result.answer,
        citations=[_citation_from_answer(c) for c in result.citations],
        coverage=result.coverage,
        not_found=result.not_found,
    )
