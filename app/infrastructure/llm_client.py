from __future__ import annotations

import json

from pydantic import BaseModel, ValidationError

from app.infrastructure.llm import LLMError, LLMProvider


class OpenAICompatibleProvider:
    """LLM provider over the OpenAI-compatible chat completions API
    (OpenAI, Groq, Ollama, LM Studio, ...)."""

    name = "openai-compatible"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature if temperature is not None else self._temperature,
                max_tokens=max_tokens or self._max_tokens,
            )
        except Exception as exc:
            raise LLMError(f"chat completion failed: {exc}") from exc
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            raise LLMError("empty completion")
        return content

    async def structured(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        try:
            resp = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                max_tokens=self._max_tokens,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            raise LLMError(f"structured completion failed: {exc}") from exc
        content = resp.choices[0].message.content if resp.choices else None
        if not content:
            raise LLMError("empty structured completion")
        return parse_schema_json(content, schema)


def parse_schema_json(content: str, schema: type[BaseModel]) -> BaseModel:
    """Parse and validate provider JSON against a schema; raise LLMError
    with a repair hint when invalid so the gateway can re-prompt."""
    try:
        payload = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LLMError(f"invalid JSON from provider: {exc}") from exc
    try:
        return schema.model_validate(payload)
    except ValidationError as exc:
        raise LLMError(f"schema validation failed: {exc}") from exc
