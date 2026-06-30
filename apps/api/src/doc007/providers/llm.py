"""LLM providers (text generation).

- OpenRouterLLMProvider: real answers via OpenRouter's OpenAI-compatible API.
- MockLLMProvider: deterministic, grounded-looking answer used in tests and
  when OPENROUTER_API_KEY is unset so the Q&A flow runs without a key.

`get_llm_provider()` picks based on settings.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from doc007.core.config import settings
from doc007.core.logging import get_logger
from doc007.providers.base import ChatMessage, LLMProvider, LLMResult

log = get_logger(__name__)


class MockLLMProvider(LLMProvider):
    @property
    def name(self) -> str:
        return "mock"

    async def complete(self, messages: list[ChatMessage], **kwargs) -> LLMResult:
        user = next((m for m in reversed(messages) if m.role == "user"), None)
        question = ""
        if user and "Question:" in user.content:
            question = user.content.split("Question:", 1)[1].strip()
        has_context = bool(user and "<context>" in user.content)
        if has_context:
            content = (
                f"Based on the provided documents, here is the answer to "
                f"'{question}'. The relevant policy is described in the source [1]."
            )
        else:
            content = "I couldn't find this in your documents."
        prompt_tokens = sum(len(m.content.split()) for m in messages)
        return LLMResult(
            content=content,
            model=self.name,
            prompt_tokens=prompt_tokens,
            completion_tokens=len(content.split()),
        )

    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        result = await self.complete(messages, **kwargs)
        for word in result.content.split():
            yield word + " "


class OpenRouterLLMProvider(LLMProvider):
    def __init__(self, *, api_key: str, base_url: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    @property
    def name(self) -> str:
        return self._model

    async def complete(self, messages: list[ChatMessage], **kwargs) -> LLMResult:
        from tenacity import retry, stop_after_attempt, wait_exponential

        @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=15))
        async def _call() -> LLMResult:
            payload: list[Any] = [{"role": m.role, "content": m.content} for m in messages]
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=payload,
                temperature=kwargs.get("temperature", 0.1),
            )
            usage = resp.usage
            return LLMResult(
                content=resp.choices[0].message.content or "",
                model=self._model,
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            )

        return await _call()

    async def stream(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[str]:
        payload: list[Any] = [{"role": m.role, "content": m.content} for m in messages]
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=payload,
            temperature=kwargs.get("temperature", 0.1),
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


def get_llm_provider() -> LLMProvider:
    if settings.openrouter_api_key:
        return OpenRouterLLMProvider(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            model=settings.llm_model,
        )
    log.warning("no_openrouter_key_using_mock_llm")
    return MockLLMProvider()
