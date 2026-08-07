from __future__ import annotations

from pydantic import BaseModel, Field


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
