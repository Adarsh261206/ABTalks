"""API boundary models.

Contract schemas for the HTTP layer. Domain models are re-exported here for
backwards-compatible imports; the definitions live in `app.domain.*`.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.candidate import CandidateProfile, Member, Mission, Signals
from app.domain.interview import Feedback

SESSION_ID_MAX = 128

__all__ = [
    "CandidateProfile",
    "Member",
    "Mission",
    "Signals",
    "Feedback",
    "InterviewRequest",
    "InterviewResponse",
    "ErrorResponse",
    "SessionView",
]


class InterviewRequest(BaseModel):
    sessionId: str
    message: str | None = None
    candidate: CandidateProfile | None = None

    @field_validator("sessionId")
    @classmethod
    def _clean_session_id(cls, v: str) -> str:
        v = v.strip()
        if not v or len(v) > SESSION_ID_MAX:
            raise ValueError("sessionId must be 1-128 characters")
        if any(ord(c) < 32 for c in v):
            raise ValueError("sessionId contains control characters")
        return v


class InterviewResponse(BaseModel):
    reply: str
    done: bool
    feedback: Feedback | None = None


class ErrorResponse(BaseModel):
    error: str
    hint: str | None = None
    request_id: str = ""


class SessionView(BaseModel):
    model_config = ConfigDict(extra="allow")

    session_id: str
    status: str
    turn_count: int
    covered_days: list[int]
    completed_days: list[int] = Field(default_factory=list)
    transcript: list[dict[str, Any]]
    report: Feedback | None = None
