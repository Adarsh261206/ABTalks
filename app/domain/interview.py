from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.candidate import CandidateProfile


class Feedback(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)


class TranscriptEntry(BaseModel):
    role: Literal["interviewer", "candidate"]
    text: str
    day: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)


class Question(BaseModel):
    day: int
    text: str
    difficulty: Literal["L1", "L2", "L3"] = "L1"
    type: Literal["concept", "apply", "scenario", "design", "probe"] = "concept"


class EngineTurn(BaseModel):
    reply: str
    done: bool = False
    feedback: Feedback | None = None


class InterviewState(BaseModel):
    session_id: str
    status: Literal["active", "completed"] = "active"
    phase: str = "warmup"
    turn_count: int = 0
    candidate: CandidateProfile | None = None
    transcript: list[TranscriptEntry] = Field(default_factory=list)
    asked: list[Question] = Field(default_factory=list)
    covered_days: list[int] = Field(default_factory=list)
    belief: dict[str, list[float]] = Field(default_factory=dict)
    plan: list[dict[str, Any]] = Field(default_factory=list)
    report: Feedback | None = None
    completed_reason: str | None = None
