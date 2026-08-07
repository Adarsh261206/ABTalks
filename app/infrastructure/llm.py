from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class LLMError(Exception):
    """Provider-level failure (timeout, outage, invalid response)."""


class LLMProvider(Protocol):
    """Raw completion provider. Implementations: MockLLMProvider (offline
    demo/tests) and OpenAICompatibleProvider (OpenAI, Groq, Ollama, ...)."""

    name: str

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        """Return the assistant's reply text."""
        ...

    async def structured(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        """Return a schema-validated model. Raises LLMError on invalid output."""
        ...
