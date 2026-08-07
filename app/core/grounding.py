"""Grounding layer (M4): candidate answers -> curriculum evidence.

Deterministic, pure arithmetic: picks the learning objective an answer
addresses (token overlap), detects which expected concepts the candidate
covered, and produces the structured EvidenceBundle (the reasoning metadata
the frontend renders later — this is product metadata, not chain-of-thought).
Confidence is explicit: low retrieval confidence is flagged in the note, never
hidden (PLANNING.md M4 grounding rules).
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.curriculum import DayInfo
from app.core.retrieval import (
    RetrievedChunk,
    objective_keywords,
    phrase_matches,
    retrieve_day,
    significant_tokens,
)

_TOP_OBJECTIVES = 2

_LOW_CONFIDENCE_THRESHOLD = 0.6


class Grounding(BaseModel):
    """What the deterministic pipeline retrieved and detected for one answer."""

    curriculum_day: int | None = None
    module: str = ""
    title: str = ""
    learning_objective: str = ""
    retrieved_chunks: list[RetrievedChunk] = Field(default_factory=list)
    retrieval_confidence: float = 0.0
    grading_confidence: float = 0.0
    concepts_expected: list[str] = Field(default_factory=list)
    concepts_detected: list[str] = Field(default_factory=list)
    concepts_missing: list[str] = Field(default_factory=list)
    note: str = ""


class EvidenceBundle(Grounding):
    """Grounding plus the graded outcome: reason, follow-up rationale and the
    belief change the grade caused."""

    reason: str = ""
    followup_reason: str | None = None
    mastery_delta: float | None = None


def ground_answer(
    day: int | None, day_info: DayInfo | None, answer: str
) -> Grounding:
    """Run the retrieval + detection pipeline for one candidate answer.

    Retrieves the day's objectives and tools, picks the objective the answer
    most addresses, and classifies expected concepts as detected/missing.
    Returns a Grounding with explicit confidence; when the curriculum is
    unavailable the confidence is 0 and the note says so."""
    if day is None or day_info is None:
        return Grounding(
            curriculum_day=day,
            retrieval_confidence=0.0,
            grading_confidence=0.0,
            note="No curriculum evidence available — evaluation is ungrounded.",
        )
    result = retrieve_day({day: day_info}, day, top_objectives=_TOP_OBJECTIVES)
    if not result.concepts:
        return Grounding(
            curriculum_day=day,
            retrieval_confidence=0.0,
            grading_confidence=0.0,
            note=result.note or "No curriculum evidence available for this day.",
        )
    answer_terms = significant_tokens(answer)
    objective = _relevant_objective(day_info.objectives, answer_terms)
    concepts = [c for c in day_info.tools if c.strip()]
    for keyword in objective_keywords(objective):
        if keyword not in concepts:
            concepts.append(keyword)
    detected = [c for c in concepts if phrase_matches(c, answer_terms)]
    missing = [c for c in concepts if c not in detected]

    concept_terms = set()
    for c in concepts:
        concept_terms |= _phrase_tokens(c)
    coverage = (
        len(answer_terms & concept_terms) / len(answer_terms) if answer_terms else 0.0
    )
    recall = len(detected) / len(concepts) if concepts else 0.0
    retrieval_confidence = round(0.4 + 0.6 * coverage, 2)
    grading_confidence = round(0.5 * retrieval_confidence + 0.5 * recall, 2)

    note = (
        "Low retrieval confidence — the answer overlapped few expected "
        "concepts; grading leans on general heuristics."
        if retrieval_confidence < _LOW_CONFIDENCE_THRESHOLD
        else "Answer grounded against the retrieved curriculum evidence."
    )
    return Grounding(
        curriculum_day=day,
        module=day_info.module,
        title=day_info.title,
        learning_objective=objective,
        retrieved_chunks=result.chunks,
        retrieval_confidence=retrieval_confidence,
        grading_confidence=grading_confidence,
        concepts_expected=concepts,
        concepts_detected=detected,
        concepts_missing=missing,
        note=note,
    )


def _relevant_objective(objectives: list[str], answer_terms: set[str]) -> str:
    """The objective the answer most addresses (highest token overlap)."""
    if not objectives:
        return ""
    best = objectives[0]
    best_score = -1
    for objective in objectives:
        score = len(answer_terms & significant_tokens(objective))
        if score > best_score:
            best_score = score
            best = objective
    return best


def _phrase_tokens(phrase: str) -> set[str]:
    return significant_tokens(phrase) or {
        t for t in phrase.lower().split() if t
    }
