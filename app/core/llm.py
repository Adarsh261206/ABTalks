from __future__ import annotations

import asyncio
import logging
from typing import Callable

from pydantic import BaseModel

from app.infrastructure.llm import LLMError, LLMProvider

logger = logging.getLogger("viva.llm")


class LLMGatewayError(Exception):
    """All retries, schema re-prompts and fallbacks exhausted."""


class LLMGateway:
    """Resilience wrapper around an LLM provider (PLANNING.md Phase 11):
    retry with backoff → schema re-prompt loop → fallback provider.

    M2 agents call this gateway exclusively; the app never talks to a
    provider directly."""

    def __init__(
        self,
        primary: LLMProvider,
        fallback: LLMProvider | None = None,
        max_retries: int = 2,
        max_schema_reprompts: int = 2,
        base_backoff: float = 0.3,
        sleep: Callable[[float], object] = asyncio.sleep,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._max_retries = max_retries
        self._max_schema_reprompts = max_schema_reprompts
        self._base_backoff = base_backoff
        self._sleep = sleep

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._primary.chat(
                    messages=messages, temperature=temperature, max_tokens=max_tokens
                )
            except LLMError as exc:
                last_error = exc
                await self._backoff(attempt)
        if self._fallback is not None:
            try:
                return await self._fallback.chat(
                    messages=messages, temperature=temperature, max_tokens=max_tokens
                )
            except LLMError as exc:
                last_error = exc
        raise LLMGatewayError(f"all LLM attempts failed: {last_error}") from last_error

    async def structured(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        attempt_msgs = list(messages)
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await self._primary.structured(
                    messages=attempt_msgs, schema=schema, temperature=temperature
                )
            except LLMError as exc:
                last_error = exc
                if attempt < self._max_schema_reprompts:
                    attempt_msgs = self._reprompt(attempt_msgs, schema, exc)
                    await self._backoff(attempt)
        if self._fallback is not None:
            try:
                return await self._fallback.structured(
                    messages=attempt_msgs, schema=schema, temperature=temperature
                )
            except LLMError as exc:
                last_error = exc
        raise LLMGatewayError(
            f"structured LLM failed: {last_error}"
        ) from last_error

    def _reprompt(self, messages: list[dict], schema: type[BaseModel], exc: LLMError) -> list[dict]:
        repair = {
            "role": "user",
            "content": (
                "Your previous response failed validation. Return ONLY valid JSON "
                f"matching the required schema. Validation error: {exc}. "
                f"Expected schema: {schema.model_json_schema()}"
            ),
        }
        return [*messages, repair]

    async def _backoff(self, attempt: int) -> None:
        await self._sleep(self._base_backoff * (2**attempt))
