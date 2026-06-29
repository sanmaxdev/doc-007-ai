"""Shared pytest fixtures.

Tests run against an in-memory SQLite DB (StaticPool keeps a single
connection so the schema persists across sessions). The `get_db`
dependency is overridden so the app uses the test database.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

import doc007.db.models  # noqa: F401  (register models on Base.metadata)
from doc007.db.base import Base, get_db
from doc007.main import app


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def client(db_engine) -> AsyncGenerator[AsyncClient, None]:
    test_session = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---- helpers -------------------------------------------------------------

API = "/api/v1"


async def register_and_login(
    client: AsyncClient, email: str, password: str = "password123"
) -> dict:
    """Register a user and return Authorization headers for them."""
    await client.post(
        f"{API}/auth/register",
        json={"email": email, "password": password, "full_name": email.split("@")[0]},
    )
    resp = await client.post(
        f"{API}/auth/login", json={"email": email, "password": password}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with maker() as s:
        yield s


class FakeVectorStore:
    """In-memory stand-in for QdrantVectorStore used in tests."""

    def __init__(self) -> None:
        self.points: dict = {}

    async def ensure_collection(self) -> None:
        return None

    async def upsert(self, points) -> None:
        for p in points:
            self.points[p.id] = p

    async def delete_document(self, workspace_id, document_id) -> None:
        wid, did = str(workspace_id), str(document_id)
        self.points = {
            k: v
            for k, v in self.points.items()
            if not (v.payload.get("workspace_id") == wid and v.payload.get("document_id") == did)
        }

    async def search(self, *, workspace_id, vector, top_k, document_ids=None) -> list:
        from doc007.rag.vector_store import SearchHit

        wid = str(workspace_id)
        dids = {str(d) for d in document_ids} if document_ids else None
        hits = []
        for p in self.points.values():
            if p.payload.get("workspace_id") != wid:
                continue
            if dids is not None and p.payload.get("document_id") not in dids:
                continue
            hits.append(SearchHit(chunk_id=p.payload["chunk_id"], score=0.9, payload=p.payload))
        return hits[:top_k]
