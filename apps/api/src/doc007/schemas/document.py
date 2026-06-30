"""Document request/response schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from doc007.db.models.document import DocumentStatus


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str


class TagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=60)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    original_filename: str
    mime_type: str
    file_size_bytes: int
    page_count: int | None
    chunk_count: int
    status: DocumentStatus
    error_message: str | None
    uploaded_by: uuid.UUID | None
    created_at: datetime
    processed_at: datetime | None
    tags: list[TagOut] = []


class ChunkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    chunk_index: int
    page_number: int | None
    token_count: int
    content: str
