from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

SESSION_ID_MAX = 128


class Mission(BaseModel):
    day: int
    title: str = ""
    passed: bool = False
    attempts: int = 0
    skipped: bool = False


class Member(BaseModel):
    id: str
    name: str = ""
    jobRole: str = ""
    yearsExperience: int = 0
    education: str = ""
    status: str = ""


class Signals(BaseModel):
    commitDays: int = 0
    missionsCompleted: int = 0
    missionsFirstTry: int = 0


class CandidateProfile(BaseModel):
    member: Member
    missions: list[Mission] = Field(default_factory=list)
    signals: Signals | None = None

    @property
    def display_name(self) -> str:
        return self.member.name or "Candidate"


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


class Feedback(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    next: list[str] = Field(default_factory=list)


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
    transcript: list[dict[str, Any]]
    report: Feedback | None = None
