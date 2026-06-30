"""Workspace analytics schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class TopDocument(BaseModel):
    document_id: uuid.UUID | None
    filename: str
    citations: int


class QuestionItem(BaseModel):
    question: str
    answered: bool
    created_at: datetime


class AnalyticsOut(BaseModel):
    total_questions: int
    answered: int
    unanswered: int
    answer_rate: float
    feedback_helpful: int
    feedback_not_helpful: int
    top_documents: list[TopDocument]
    recent_questions: list[QuestionItem]
    unanswered_questions: list[QuestionItem]
