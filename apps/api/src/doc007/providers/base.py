"""Provider interfaces.

The LLM (generation) and embedding providers are intentionally decoupled:
- LLM         -> OpenRouter (OpenAI-compatible chat/completions)
- Embeddings  -> OpenAI text-embedding-3-small (OpenRouter has no embeddings)

Concrete implementations land in Phase 2/3.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str


@dataclass
class LLMResult:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LLMProvider(ABC):
    """Text generation provider (OpenRouter)."""

    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def complete(self, messages: list[ChatMessage], **kwargs) -> LLMResult: ...


class EmbeddingProvider(ABC):
    """Embedding provider (OpenAI). Output dimension must equal settings.vector_dim."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier stored alongside each chunk (for traceability)."""

    @property
    @abstractmethod
    def dimension(self) -> int: ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
