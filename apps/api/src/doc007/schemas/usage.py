"""Usage summary schema."""

from __future__ import annotations

from pydantic import BaseModel


class UsageByDay(BaseModel):
    date: str
    count: int


class UsageSummaryOut(BaseModel):
    questions_this_period: int
    monthly_question_limit: int | None
    total_documents: int
    total_chunks: int
    storage_used_bytes: int
    total_tokens_in: int
    total_tokens_out: int
    total_cost_estimate: float
    questions_by_day: list[UsageByDay]
