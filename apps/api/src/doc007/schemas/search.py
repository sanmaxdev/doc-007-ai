"""Retrieval debug/eval schemas."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class RetrieveRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[uuid.UUID] | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)
    hybrid: bool | None = None


class RetrievedChunkOut(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_filename: str
    page_number: int | None
    chunk_index: int
    content: str
    score: float
    lexical_score: float
    fused_score: float
    dense_rank: int | None
    lexical_rank: int | None


class RetrieveResponse(BaseModel):
    question: str
    method: str
    not_found: bool
    chunks: list[RetrievedChunkOut]
    prompt: str
