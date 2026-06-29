"""Vector store abstraction over Qdrant.

Every search is filtered by `workspace_id` server-side. That filter is the
hard boundary for tenant isolation in the vector layer, so it is applied here
and never taken from the client.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass

from doc007.core.config import settings


@dataclass
class VectorPoint:
    id: str
    vector: list[float]
    payload: dict


@dataclass
class SearchHit:
    chunk_id: str
    score: float
    payload: dict


class VectorStore(ABC):
    @abstractmethod
    async def ensure_collection(self) -> None: ...

    @abstractmethod
    async def upsert(self, points: list[VectorPoint]) -> None: ...

    @abstractmethod
    async def delete_document(self, workspace_id: uuid.UUID, document_id: uuid.UUID) -> None: ...

    @abstractmethod
    async def search(
        self,
        *,
        workspace_id: uuid.UUID,
        vector: list[float],
        top_k: int,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[SearchHit]: ...


class QdrantVectorStore(VectorStore):
    def __init__(self) -> None:
        self._client = None
        self._collection = settings.qdrant_collection

    def _get_client(self):
        if self._client is None:
            from qdrant_client import AsyncQdrantClient

            self._client = AsyncQdrantClient(
                url=settings.qdrant_url, api_key=settings.qdrant_api_key or None
            )
        return self._client

    async def ensure_collection(self) -> None:
        from qdrant_client.models import Distance, VectorParams

        client = self._get_client()
        collections = await client.get_collections()
        if self._collection in {c.name for c in collections.collections}:
            return
        await client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=settings.vector_dim, distance=Distance.COSINE),
        )
        for field in ("workspace_id", "document_id"):
            await client.create_payload_index(
                collection_name=self._collection, field_name=field, field_schema="keyword"
            )

    async def upsert(self, points: list[VectorPoint]) -> None:
        from qdrant_client.models import PointStruct

        if not points:
            return
        client = self._get_client()
        await client.upsert(
            collection_name=self._collection,
            points=[
                PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points
            ],
        )

    async def delete_document(self, workspace_id: uuid.UUID, document_id: uuid.UUID) -> None:
        from qdrant_client.models import (
            FieldCondition,
            Filter,
            FilterSelector,
            MatchValue,
        )

        client = self._get_client()
        selector = FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(key="workspace_id", match=MatchValue(value=str(workspace_id))),
                    FieldCondition(key="document_id", match=MatchValue(value=str(document_id))),
                ]
            )
        )
        await client.delete(collection_name=self._collection, points_selector=selector)

    async def search(
        self,
        *,
        workspace_id: uuid.UUID,
        vector: list[float],
        top_k: int,
        document_ids: list[uuid.UUID] | None = None,
    ) -> list[SearchHit]:
        from qdrant_client.models import FieldCondition, Filter, MatchAny, MatchValue

        must: list = [
            FieldCondition(key="workspace_id", match=MatchValue(value=str(workspace_id)))
        ]
        if document_ids:
            must.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=[str(d) for d in document_ids]),
                )
            )
        client = self._get_client()
        response = await client.query_points(
            collection_name=self._collection,
            query=vector,
            query_filter=Filter(must=must),
            limit=top_k,
            with_payload=True,
        )
        return [
            SearchHit(chunk_id=str(r.id), score=r.score, payload=r.payload or {})
            for r in response.points
        ]


def get_vector_store() -> VectorStore:
    return QdrantVectorStore()
