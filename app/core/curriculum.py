from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.config import settings


class DayInfo(BaseModel):
    day: int
    title: str
    type: str = ""
    objectives: list[str] = []
    tools: list[str] = []


def load_curriculum(path: Path | None = None) -> dict[int, DayInfo]:
    """Load curriculum.json into {day: DayInfo}. Returns {} when unavailable
    so the engine degrades gracefully (mock/demo mode)."""
    try:
        data = json.loads((path or settings.curriculum_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return {
        int(day["day"]): DayInfo(
            day=int(day["day"]),
            title=day.get("title", ""),
            type=day.get("type", ""),
            objectives=day.get("objectives", []),
            tools=day.get("tools", []),
        )
        for day in data.get("days", [])
    }
