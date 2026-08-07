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
    module: str = ""


def load_curriculum(path: Path | None = None) -> dict[int, DayInfo]:
    """Load curriculum.json into {day: DayInfo}. Returns {} when unavailable
    so the engine degrades gracefully (mock/demo mode)."""
    try:
        data = json.loads((path or settings.curriculum_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    modules = _module_by_day(data.get("modules", []))
    return {
        int(day["day"]): DayInfo(
            day=int(day["day"]),
            title=day.get("title", ""),
            type=day.get("type", ""),
            objectives=day.get("objectives", []),
            tools=day.get("tools", []),
            module=modules.get(int(day["day"]), ""),
        )
        for day in data.get("days", [])
    }


def _module_by_day(modules: list[dict]) -> dict[int, str]:
    """Map day -> module title. Modules use inclusive [start, end] day ranges
    (e.g. {"n": 3, "days": [7, 10]} covers days 7..10)."""
    mapping: dict[int, str] = {}
    for module in modules:
        days = module.get("days", [])
        if len(days) >= 2:
            for day in range(int(days[0]), int(days[1]) + 1):
                mapping[day] = module.get("title", "")
    return mapping
