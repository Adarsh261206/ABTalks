"""Grader agent: rubric scoring of each answer (no RAG in M2).

Scores accuracy / depth / clarity / honesty on 0-5 per PLANNING.md 9.12
(weighted 0.5/0.3/0.2 + honesty bonus) with overclaim and vagueness flags.
LLM-graded when online; deterministic heuristics offline. M4 grounds
accuracy in retrieved curriculum chunks; M2 stays neutral on accuracy
because there is no retrieval yet. Also builds the probe target used by
the Director for follow-up generation (M3).
"""

from __future__ import annotations

import logging
import re

from pydantic import BaseModel, Field

from app.core.curriculum import DayInfo
from app.core.grounding import EvidenceBundle, Grounding, ground_answer
from app.core.llm import LLMGateway, LLMGatewayError
from app.core.prompts import GRADER_EVIDENCE, GRADER_SYSTEM
from app.domain.candidate import CandidateProfile
from app.domain.interview import Question

logger = logging.getLogger("viva.agents.grader")

_ACCURACY_WEIGHT = 0.5
_DEPTH_WEIGHT = 0.3
_CLARITY_WEIGHT = 0.2

_HONESTY_PHRASES = (
    "i don't know",
    "i dont know",
    "not sure",
    "i'm not sure",
    "im not sure",
    "i am not sure",
    "not certain",
    "to be honest",
    "honestly",
    "i'm guessing",
)
_VAGUE_PHRASES = (
    "stuff",
    "things like that",
    "and so on",
    "something like that",
    "i guess",
    "i dunno",
    "some stuff",
    "etc",
)
_CLAIM_VERBS = re.compile(
    r"\b(i|we)\s+(built|implemented|created|completed|finished|passed|made|did|"
    r"deployed|shipped)\b"
)


class GradeResult(BaseModel):
    """Validated grader output (PLANNING.md 17.3 schema), plus the M4
    evidence bundle that grounds the score."""

    day: int
    accuracy: float = Field(ge=0, le=5)
    depth: float = Field(ge=0, le=5)
    clarity: float = Field(ge=0, le=5)
    honesty_bonus: float = Field(default=0.0, ge=0, le=0.5)
    evidence_quotes: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    overclaim: bool = False
    overclaim_evidence: str | None = None
    vague: bool = False
    vague_evidence: str | None = None
    evidence: EvidenceBundle | None = None

    @property
    def weighted_score(self) -> float:
        raw = (
            _ACCURACY_WEIGHT * self.accuracy
            + _DEPTH_WEIGHT * self.depth
            + _CLARITY_WEIGHT * self.clarity
            + self.honesty_bonus
        )
        return max(0.0, min(5.0, raw))


class ProbeTarget(BaseModel):
    """Follow-up spec (PLANNING.md 17.4): what to probe, how, and why —
    grounded in the retrieved objective when available."""

    kind: str = "clarify"  # clarify | challenge | deepen | verify | probe
    target: str
    ref_day: int | None = None
    ref_quote: str = ""
    objective: str = ""
    detected_concepts: list[str] = Field(default_factory=list)
    missing_concepts: list[str] = Field(default_factory=list)
    followup_reason: str = ""


class _GraderOutput(BaseModel):
    accuracy: float = 0.0
    depth: float = 0.0
    clarity: float = 0.0
    honesty_bonus: float = 0.0
    evidence_quotes: list[str] = Field(default_factory=list)
    mistakes: list[str] = Field(default_factory=list)
    overclaim: bool = False
    overclaim_evidence: str | None = None
    vague: bool = False
    vague_evidence: str | None = None


class Grader:
    """Scores one answer; LLM first, deterministic heuristics fallback."""

    def __init__(self, gateway: LLMGateway, use_llm: bool = False) -> None:
        self._gateway = gateway
        self._use_llm = use_llm

    async def grade(
        self,
        question: Question,
        answer: str,
        day: DayInfo | None,
        candidate: CandidateProfile,
    ) -> GradeResult:
        grounding = ground_answer(question.day, day, answer)
        if self._use_llm:
            try:
                output = await self._gateway.structured(
                    [
                        {"role": "system", "content": GRADER_SYSTEM},
                        {
                            "role": "user",
                            "content": self._prompt(question, answer, day, candidate, grounding),
                        },
                    ],
                    schema=_GraderOutput,
                    temperature=0.0,
                )
                assert isinstance(output, _GraderOutput)
                result = self._to_result(question.day, output)
                result.evidence = self._bundle(question.day, answer, day, grounding, result)
                return result
            except (LLMGatewayError, AssertionError) as exc:
                logger.warning("grader fell back to heuristics: %s", exc)
        return self._fallback(question.day, answer, day, candidate, grounding)

    # -- LLM path ---------------------------------------------------------

    def _prompt(
        self,
        question: Question,
        answer: str,
        day: DayInfo | None,
        candidate: CandidateProfile,
        grounding: Grounding,
    ) -> str:
        objectives = "; ".join(day.objectives) if day else ""
        mission = next(
            (m for m in candidate.missions if m.day == question.day), None
        )
        mission_text = (
            f"passed={mission.passed}, skipped={mission.skipped}, attempts={mission.attempts}"
            if mission
            else "no mission record"
        )
        evidence = (
            GRADER_EVIDENCE.format(
                day=grounding.curriculum_day or "?",
                module=grounding.module or "unavailable",
                title=grounding.title or "unavailable",
                objective=grounding.learning_objective or "unavailable",
                chunks=" | ".join(c.text for c in grounding.retrieved_chunks)
                or "none retrieved",
                expected=", ".join(grounding.concepts_expected) or "none",
                detected=", ".join(grounding.concepts_detected) or "none",
                missing=", ".join(grounding.concepts_missing) or "none",
                confidence=grounding.retrieval_confidence,
                note=grounding.note,
            )
            if grounding.curriculum_day is not None
            else "No curriculum evidence could be retrieved for this question — grade "
            "conservatively and state that the evaluation is ungrounded."
        )
        return (
            f"Question: {question.text or f'Day {question.day}'}\n"
            f"Curriculum day: Day {question.day} — {day.title if day else ''}\n"
            f"Day objectives: {objectives or 'unavailable'}\n"
            f"Candidate mission record for Day {question.day}: {mission_text}\n"
            f"Candidate answer:\n{answer}\n\n{evidence}"
        )

    def _to_result(self, day: int, output: _GraderOutput) -> GradeResult:
        return GradeResult(
            day=day,
            accuracy=_clamp_score(output.accuracy),
            depth=_clamp_score(output.depth),
            clarity=_clamp_score(output.clarity),
            honesty_bonus=0.5 if output.honesty_bonus >= 0.25 else 0.0,
            evidence_quotes=output.evidence_quotes,
            mistakes=output.mistakes,
            overclaim=output.overclaim,
            overclaim_evidence=output.overclaim_evidence,
            vague=output.vague,
            vague_evidence=output.vague_evidence,
        )

    # -- deterministic fallback ---------------------------------------------

    def _fallback(
        self,
        day: int,
        answer: str,
        day_info: DayInfo | None,
        candidate: CandidateProfile,
        grounding: Grounding,
    ) -> GradeResult:
        answer_lower = answer.lower()
        length = len(answer)
        if length < 30:
            depth = 1.5
        elif length < 80:
            depth = 2.5
        elif length < 160:
            depth = 3.0
        elif length < 300:
            depth = 3.5
        elif length < 500:
            depth = 4.0
        else:
            depth = 4.5

        clarity = _clarity_score(answer)

        if grounding.concepts_expected:
            recall = len(grounding.concepts_detected) / len(grounding.concepts_expected)
            accuracy = _clamp_score(3.0 + 2.0 * (recall - 0.5))
            if len(grounding.concepts_detected) >= 3:
                depth = _clamp_score(depth + 0.5)
        else:
            recall = 0.0
            accuracy = 3.0
            if day_info and any(
                tool and tool.lower() in answer_lower for tool in day_info.tools
            ):
                accuracy = min(4.0, accuracy + 0.5)

        honesty_bonus = 0.5 if any(p in answer_lower for p in _HONESTY_PHRASES) else 0.0

        vague = any(p in answer_lower for p in _VAGUE_PHRASES)

        overclaim = False
        overclaim_evidence = None
        mission = next((m for m in candidate.missions if m.day == day), None)
        if mission is not None and not mission.passed and _CLAIM_VERBS.search(answer_lower):
            overclaim = True
            overclaim_evidence = answer.strip()[:160]

        result = GradeResult(
            day=day,
            accuracy=accuracy,
            depth=depth,
            clarity=clarity,
            honesty_bonus=honesty_bonus,
            overclaim=overclaim,
            overclaim_evidence=overclaim_evidence,
            vague=vague,
            vague_evidence=answer.strip()[:160] if vague else None,
        )
        result.evidence = self._bundle(day, answer, day_info, grounding, result)
        return result

    # -- grounding ----------------------------------------------------------

    def _bundle(
        self,
        day: int,
        answer: str,
        day_info: DayInfo | None,
        grounding: Grounding,
        result: GradeResult,
    ) -> EvidenceBundle:
        """Deterministic evidence for every score: expected objective,
        retrieved chunks, concepts covered/missed, and why the score moved."""
        bundle = EvidenceBundle(**grounding.model_dump())
        missing = ", ".join(bundle.concepts_missing[:3]) or "none"
        detected = ", ".join(bundle.concepts_detected) or "none"
        if bundle.curriculum_day is None:
            bundle.reason = (
                f"No curriculum evidence available for Day {day} — score "
                "comes from general heuristics (explicitly ungrounded)."
            )
        else:
            score_why = (
                "accuracy reflects the expected concepts the candidate "
                "actually addressed"
                if bundle.concepts_detected
                else "no expected concepts detected; accuracy penalized"
            )
            bundle.reason = (
                f"Day {day} — {bundle.title} ({bundle.module}). Expected: "
                f"{bundle.learning_objective}. Candidate covered: {detected}; "
                f"missed: {missing}. Retrieval confidence "
                f"{bundle.retrieval_confidence:.2f} ({bundle.note}) — {score_why}."
            )
        return bundle


def _clarity_score(answer: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+", answer) if s.strip()]
    if not sentences:
        return 2.0
    avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
    if len(sentences) >= 3 and 8 <= avg_words <= 30:
        return 4.5
    if 8 <= avg_words <= 30:
        return 4.0
    if avg_words < 6:
        return 3.0
    if avg_words > 40:
        return 2.5
    return 3.0


def _clamp_score(value: float) -> float:
    return max(0.0, min(5.0, value))


def build_probe_target(grade: GradeResult, answer: str, day: int) -> ProbeTarget:
    """Choose the single best grounded follow-up target (PLANNING.md 17.4):
    mistakes > overclaims > missing concepts (from the retrieved objective)
    > vagueness > deepen. Deterministic — the Interviewer renders the target
    in the VIVA voice."""
    quote = _snippet(answer)
    bundle = grade.evidence
    concepts = bundle.concepts_detected if bundle else []
    missing = bundle.concepts_missing if bundle else []
    objective = bundle.learning_objective if bundle else ""
    if grade.mistakes:
        return ProbeTarget(
            kind="challenge", target=grade.mistakes[0], ref_day=day, ref_quote=quote,
            objective=objective, detected_concepts=concepts, missing_concepts=missing,
            followup_reason=f"the answer contradicts the expected objective: {objective}",
        )
    if grade.overclaim and grade.overclaim_evidence:
        return ProbeTarget(
            kind="challenge",
            target="work you claim on this day",
            ref_day=day,
            ref_quote=_snippet(grade.overclaim_evidence),
            objective=objective, detected_concepts=concepts, missing_concepts=missing,
            followup_reason="the candidate claims work the mission record for this day does not support",
        )
    if missing:
        return ProbeTarget(
            kind="probe",
            target=missing[0],
            ref_day=day,
            ref_quote=quote,
            objective=objective, detected_concepts=concepts, missing_concepts=missing,
            followup_reason=(
                f"the candidate missed concept '{missing[0]}' expected by the "
                f"retrieved objective: {objective}"
            ),
        )
    if grade.vague:
        return ProbeTarget(
            kind="clarify", target="be more concrete", ref_day=day, ref_quote=quote,
            objective=objective, detected_concepts=concepts, missing_concepts=missing,
            followup_reason="the answer was too vague to ground against the retrieved objective",
        )
    term = _extract_term(answer)
    return ProbeTarget(
        kind="deepen",
        target=term or "your approach",
        ref_day=day,
        ref_quote=quote,
        objective=objective, detected_concepts=concepts, missing_concepts=missing,
        followup_reason=f"mastery demonstrated — deepening into '{term or 'the approach'}'",
    )


def _extract_term(answer: str) -> str:
    """Longest domain-sounding word from the answer as a deepen target."""
    words = re.findall(r"[A-Za-z][A-Za-z-]{5,}", answer)
    if not words:
        return ""
    return max(words, key=len)


def _snippet(text: str, limit: int = 100) -> str:
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")
