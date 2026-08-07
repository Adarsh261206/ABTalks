from __future__ import annotations

from typing import Any

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from app.infrastructure.llm import LLMError


class MockLLMProvider:
    """Deterministic offline provider: demo/tests never depend on keys or
    network. `chat` returns scripted replies; `structured` returns
    schema-shaped data built from defaults and dummy values."""

    name = "mock"

    def __init__(self, chat_replies: list[str] | None = None) -> None:
        self._replies = list(chat_replies or ["This is a mock assistant reply."])
        self._chat_calls = 0
        self._structured_calls = 0

    @property
    def chat_calls(self) -> int:
        return self._chat_calls

    @property
    def structured_calls(self) -> int:
        return self._structured_calls

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> str:
        self._chat_calls += 1
        return self._replies[min(self._chat_calls, len(self._replies)) - 1]

    async def structured(
        self,
        messages: list[dict],
        schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        self._structured_calls += 1
        return _mock_for_schema(schema)


def _mock_for_schema(schema: type[BaseModel]) -> BaseModel:
    """Build a schema-valid instance with deterministic dummy values."""
    values: dict[str, Any] = {}
    for name, field in schema.model_fields.items():
        if field.default is not PydanticUndefined and field.default is not None:
            values[name] = field.default
            continue
        annotation = field.annotation
        origin = getattr(annotation, "__origin__", None)
        if origin is list:
            values[name] = []
        elif annotation is str:
            values[name] = "mock"
        elif annotation is int:
            values[name] = 0
        elif annotation is float:
            values[name] = 0.0
        elif annotation is bool:
            values[name] = False
        else:
            values[name] = None
    return schema.model_validate(values)
