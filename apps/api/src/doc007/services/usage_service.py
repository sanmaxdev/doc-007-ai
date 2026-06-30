"""Usage ledger + per-workspace question quota.

`record` appends a usage event and commits its own row (append-only, like the
audit log). Quota is enforced against the workspace's monthly_question_limit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from doc007.core.config import settings
from doc007.core.exceptions import QuotaExceededError
from doc007.db.models.document import Document, DocumentChunk
from doc007.db.models.usage import UsageEvent, UsageEventType
from doc007.db.models.workspace import Workspace


def estimate_cost(tokens_in: int, tokens_out: int) -> float:
    return round(
        tokens_in / 1000 * settings.cost_per_1k_input_tokens
        + tokens_out / 1000 * settings.cost_per_1k_output_tokens,
        6,
    )


def _month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


async def record(
    db: AsyncSession,
    *,
    workspace_id: uuid.UUID,
    user_id: uuid.UUID | None,
    event_type: UsageEventType,
    source: str = "app",
    tokens_in: int = 0,
    tokens_out: int = 0,
) -> None:
    db.add(
        UsageEvent(
            workspace_id=workspace_id,
            user_id=user_id,
            event_type=event_type,
            source=source,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_estimate=estimate_cost(tokens_in, tokens_out),
        )
    )
    await db.commit()


async def questions_this_period(db: AsyncSession, workspace_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(UsageEvent)
        .where(
            UsageEvent.workspace_id == workspace_id,
            UsageEvent.event_type == UsageEventType.question,
            UsageEvent.created_at >= _month_start(),
        )
    )
    return int(result.scalar_one())


async def check_question_quota(db: AsyncSession, workspace: Workspace) -> None:
    limit = workspace.monthly_question_limit
    if limit is None:
        return
    used = await questions_this_period(db, workspace.id)
    if used >= limit:
        raise QuotaExceededError(
            f"Monthly question limit reached ({used}/{limit}). "
            "Raise the limit in workspace settings or wait for the next period."
        )


async def usage_summary(db: AsyncSession, workspace: Workspace) -> dict:
    wid = workspace.id

    totals = await db.execute(
        select(
            func.coalesce(func.sum(UsageEvent.tokens_in), 0),
            func.coalesce(func.sum(UsageEvent.tokens_out), 0),
            func.coalesce(func.sum(UsageEvent.cost_estimate), 0.0),
        ).where(UsageEvent.workspace_id == wid)
    )
    tokens_in, tokens_out, cost = totals.one()

    doc_count = await db.scalar(
        select(func.count()).select_from(Document).where(Document.workspace_id == wid)
    )
    chunk_count = await db.scalar(
        select(func.count()).select_from(DocumentChunk).where(DocumentChunk.workspace_id == wid)
    )

    # Daily question counts for the last 14 days, bucketed in Python for portability.
    since = datetime.now(UTC) - timedelta(days=14)
    rows = await db.execute(
        select(UsageEvent.created_at).where(
            UsageEvent.workspace_id == wid,
            UsageEvent.event_type == UsageEventType.question,
            UsageEvent.created_at >= since,
        )
    )
    by_day: dict[str, int] = {}
    for (created_at,) in rows.all():
        day = created_at.date().isoformat()
        by_day[day] = by_day.get(day, 0) + 1

    return {
        "questions_this_period": await questions_this_period(db, wid),
        "monthly_question_limit": workspace.monthly_question_limit,
        "total_documents": int(doc_count or 0),
        "total_chunks": int(chunk_count or 0),
        "storage_used_bytes": workspace.storage_used_bytes,
        "total_tokens_in": int(tokens_in or 0),
        "total_tokens_out": int(tokens_out or 0),
        "total_cost_estimate": round(float(cost or 0.0), 6),
        "questions_by_day": [{"date": d, "count": c} for d, c in sorted(by_day.items())],
    }
