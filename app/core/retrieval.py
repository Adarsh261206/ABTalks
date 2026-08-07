"""Deterministic curriculum retrieval (M4) — the RAG layer.

No external frameworks: a small lexical index over the curriculum JSON (the
single source of truth) that retrieves the smallest useful evidence — one
objective or one tool — never a whole document (PLANNING.md M4). Day-exact
retrieval powers grading (the question pins the day); topic retrieval ranks
days by token overlap when the topic is unknown and flags ambiguity. Both
paths are pure functions of the curriculum, so results are reproducible.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from app.core.curriculum import DayInfo

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for",
    "with", "your", "you", "into", "from", "that", "this", "it", "is",
    "are", "was", "were", "be", "been", "can", "could", "will", "would",
    "should", "did", "does", "do", "have", "has", "had", "not", "its",
    "their", "then", "than", "at", "by", "as", "up", "down", "out", "use",
    "using", "used", "set", "get", "make", "also", "after", "before",
}

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'\-]*")

_MIN_TERM_LEN = 4


def tokens(text: str) -> set[str]:
    """Normalized significant tokens: lowercase, punctuation stripped,
    stopwords removed."""
    return {
        m.group(0)
        for m in _TOKEN_RE.finditer(text.lower())
        if m.group(0) not in _STOPWORDS
    }


def significant_tokens(text: str) -> set[str]:
    """Tokens long enough to carry meaning (>= 4 chars)."""
    return {t for t in tokens(text) if len(t) >= _MIN_TERM_LEN}


def objective_keywords(objective: str) -> list[str]:
    """Deterministic concept list from an objective's wording."""
    return sorted(significant_tokens(objective))


def phrase_matches(phrase: str, answer_tokens: set[str]) -> bool:
    """A phrase (tool or keyword) is covered when every one of its tokens
    appears in the candidate's answer."""
    return bool(phrase.strip()) and phrase_tokens(phrase) <= answer_tokens


def phrase_tokens(phrase: str) -> set[str]:
    return tokens(phrase)


class RetrievedChunk(BaseModel):
    """Smallest useful evidence unit: one objective or one tool."""

    kind: Literal["objective", "tool"] = "objective"
    text: str


class RetrievalResult(BaseModel):
    """Output of one retrieval call: the day, its chunks, expected concepts,
    and a deterministic confidence score."""

    day: int | None = None
    module: str = ""
    title: str = ""
    chunks: list[RetrievedChunk] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    ambiguous: bool = False
    note: str = ""


class CurriculumIndex:
    """Lexical index over the curriculum days; topic retrieval."""

    def __init__(self, curriculum: dict[int, DayInfo]) -> None:
        self._days = curriculum
        self._day_tokens = {
            day: significant_tokens(f"{info.title} {' '.join(info.objectives)}")
            for day, info in curriculum.items()
        }

    def retrieve_topic(self, query: str, k: int = 1) -> RetrievalResult:
        """Rank days by overlap with the query; flag ambiguity when the top
        two candidates score within 10% of each other."""
        query_terms = significant_tokens(query)
        if not query_terms:
            return RetrievalResult(
                confidence=0.0,
                ambiguous=True,
                note="Query carried no significant terms — no topic could be retrieved.",
            )
        scored = sorted(
            (
                (len(query_terms & day_terms), day)
                for day, day_terms in self._day_tokens.items()
            ),
            key=lambda item: (-item[0], item[1]),
        )
        if not scored or scored[0][0] == 0:
            return RetrievalResult(
                confidence=0.0,
                ambiguous=True,
                note="No curriculum day matched the query terms.",
            )
        top_score, top_day = scored[0]
        second_score = scored[1][0] if len(scored) > 1 else 0
        ambiguous = second_score > 0 and (top_score - second_score) <= max(
            1, top_score * 0.1
        )
        return RetrievalResult(
            day=top_day,
            module=self._days[top_day].module,
            title=self._days[top_day].title,
            confidence=round(top_score / (top_score + second_score), 2),
            ambiguous=ambiguous,
            note="Topic ranked by lexical overlap with curriculum day text.",
        )


def retrieve_day(
    curriculum: dict[int, DayInfo], day: int, top_objectives: int = 2
) -> RetrievalResult:
    """Day-exact retrieval: the day's objectives and tools as the smallest
    useful chunks. Confidence 1.0 — the day is pinned by the question."""
    info = curriculum.get(day)
    if info is None:
        return RetrievalResult(
            day=day,
            confidence=0.0,
            note="Curriculum unavailable for this day — retrieval is ungrounded.",
        )
    chunks = [
        RetrievedChunk(kind="objective", text=o) for o in info.objectives[:top_objectives]
    ]
    chunks += [RetrievedChunk(kind="tool", text=t) for t in info.tools if t.strip()]
    concepts: list[str] = []
    for tool in info.tools:
        if tool.strip():
            concepts.append(tool)
    for objective in info.objectives[:top_objectives]:
        for keyword in objective_keywords(objective):
            if keyword not in concepts:
                concepts.append(keyword)
    return RetrievalResult(
        day=day,
        module=info.module,
        title=info.title,
        chunks=chunks,
        concepts=concepts,
        confidence=1.0,
        note="Day-exact retrieval: the question pinned this curriculum day.",
    )
