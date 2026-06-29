"""Embedding providers.

- OpenAIEmbeddingProvider: real embeddings (text-embedding-3-small, 1536-d).
- MockEmbeddingProvider: deterministic vectors, used in tests and whenever
  OPENAI_API_KEY is unset so the whole pipeline is runnable without a key.

`get_embedding_provider()` picks based on settings.
"""

from __future__ import annotations

import hashlib
import math
import random

from doc007.core.config import settings
from doc007.core.logging import get_logger
from doc007.providers.base import EmbeddingProvider

log = get_logger(__name__)


class MockEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dimension: int) -> None:
        self._dimension = dimension

    @property
    def name(self) -> str:
        return "mock"

    @property
    def dimension(self) -> int:
        return self._dimension

    def _vector(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        vec = [rng.uniform(-1.0, 1.0) for _ in range(self._dimension)]
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, api_key: str, model: str, dimension: int) -> None:
        from openai import AsyncOpenAI  # lazy: keep import cost out of cold paths

        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimension = dimension

    @property
    def name(self) -> str:
        return self._model

    @property
    def dimension(self) -> int:
        return self._dimension

    async def embed(self, texts: list[str]) -> list[list[float]]:
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=1, max=20))
        async def _call(batch: list[str]) -> list[list[float]]:
            resp = await self._client.embeddings.create(model=self._model, input=batch)
            return [d.embedding for d in resp.data]

        # OpenAI accepts batched input; chunk to stay well under limits.
        out: list[list[float]] = []
        for i in range(0, len(texts), 128):
            out.extend(await _call(texts[i : i + 128]))
        return out


def get_embedding_provider() -> EmbeddingProvider:
    if settings.openai_api_key:
        return OpenAIEmbeddingProvider(
            api_key=settings.openai_api_key,
            model=settings.embedding_model,
            dimension=settings.vector_dim,
        )
    log.warning("no_openai_key_using_mock_embeddings")
    return MockEmbeddingProvider(settings.vector_dim)
