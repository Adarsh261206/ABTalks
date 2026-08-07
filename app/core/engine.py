from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.config import settings
from app.schemas import CandidateProfile, Feedback
from app.state.models import InterviewState, TranscriptEntry

END_KEYWORDS = {
    "end",
    "exit",
    "stop",
    "finish",
    "done",
    "/end",
    "/exit",
    "/finish",
    "i am done",
    "i'm done",
    "im done",
    "that's it",
    "thats it",
    "that is it",
    "let's wrap up",
    "lets wrap up",
    "wrap up",
    "wrapup",
}

# Core curriculum days, per PLANNING.md (Phase 6/9). M2 replaces this static
# sequence with the adaptive Director; the contract, invariants and shape stay.
DEFAULT_QUESTION_DAYS = [7, 8, 10, 12, 16, 22, 23, 31]

PHASES = {"warmup": (1, 2), "core": (3, 6), "scenario": (7, 8)}


@dataclass
class EngineTurn:
    reply: str
    done: bool = False
    feedback: Feedback | None = None


class InterviewEngine:
    """M1 core: deterministic, spec-compliant interview state machine.
    M2+ swaps the question source for the adaptive Director/Grader/Prober agents
    without changing the contract, state shape, or invariants."""

    def __init__(
        self,
        curriculum_path: Path | None = None,
        default_questions: int = settings.default_questions,
        max_turns: int = settings.max_turns,
    ) -> None:
        self.default_questions = default_questions
        self.max_turns = max_turns
        self.curriculum = self._load_curriculum(curriculum_path or settings.curriculum_path)

    def _load_curriculum(self, path: Path) -> dict[int, dict]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        days = {}
        for day in data.get("days", []):
            days[int(day["day"])] = {
                "title": day.get("title", ""),
                "type": day.get("type", ""),
                "objectives": day.get("objectives", []),
                "tools": day.get("tools", []),
            }
        return days

    # -- lifecycle -------------------------------------------------------

    def start(self, state: InterviewState, candidate: CandidateProfile) -> str:
        state.candidate = candidate
        state.plan = [
            {"day": d, "type": "concept", "difficulty": "L1"}
            for d in self._question_days()
        ]
        welcome = f"Welcome, {candidate.display_name}. Let's begin your interview."
        state.transcript.append(TranscriptEntry(role="interviewer", text=welcome))
        return welcome

    def process(self, state: InterviewState, message: str) -> EngineTurn:
        state.turn_count += 1
        state.transcript.append(
            TranscriptEntry(role="candidate", text=message, meta={"turn": state.turn_count})
        )

        normalized = " ".join(message.lower().split())
        asked = len(state.asked)
        force_wrap = (
            state.turn_count >= self.max_turns
            or asked >= self.default_questions
            or normalized in END_KEYWORDS
        )

        if force_wrap:
            return self._wrap_up(state, reason="completed")

        return self._ask_next(state)

    # -- interview flow ----------------------------------------------------

    def _question_days(self) -> list[int]:
        days = [d for d in DEFAULT_QUESTION_DAYS if d in self.curriculum]
        if not days:
            days = DEFAULT_QUESTION_DAYS
        return days

    def _ask_next(self, state: InterviewState) -> EngineTurn:
        days = self._question_days()
        day_no = days[len(state.asked)]
        question = self._build_question(day_no, state)
        state.asked.append(
            {"day": day_no, "text": question, "difficulty": "L1", "type": "concept"}
        )
        if day_no not in state.covered_days:
            state.covered_days.append(day_no)
        state.transcript.append(
            TranscriptEntry(role="interviewer", text=question, day=day_no)
        )
        state.phase = self._phase_for(len(state.asked))
        return EngineTurn(reply=question)

    def _build_question(self, day_no: int, state: InterviewState) -> str:
        day = self.curriculum.get(day_no)
        if day is None:
            return f"Let's talk about Day {day_no}. What did you build that day?"
        objective = day["objectives"][0] if day["objectives"] else ""
        stem = self._humanize(objective.rstrip(".").strip())
        if not stem:
            return f"Let's talk about Day {day_no} — {day['title']}. Tell me about your work on it."
        return f"Let's talk about Day {day_no} — {day['title']}. {stem}?"

    @staticmethod
    def _humanize(objective: str) -> str:
        """Turn a curriculum objective into a natural interviewer question."""
        mapping = (
            ("Understand how ", "Walk me through how "),
            ("Understand ", "Explain "),
            ("Learn ", "Explain "),
            ("Build ", "Walk me through how you built "),
            ("Create ", "Walk me through how you created "),
            ("Implement ", "Walk me through how you implemented "),
            ("Generate ", "Walk me through how you generated "),
            ("Design ", "Walk me through how you designed "),
            ("Set up ", "Walk me through how you set up "),
            ("Install ", "Walk me through how you installed "),
            ("Configure ", "Walk me through how you configured "),
            ("Connect ", "Walk me through how you connected "),
            ("Integrate ", "Walk me through how you integrated "),
            ("Demonstrate ", "Walk me through how you demonstrated "),
            ("Showcase ", "Walk me through how you showcased "),
            ("Present ", "Walk me through how you presented "),
            ("Publish ", "Walk me through how you published "),
            ("Complete ", "Walk me through how you completed "),
            ("Prepare ", "Walk me through how you prepared "),
            ("Finalize ", "Walk me through how you finalized "),
            ("Verify ", "How did you verify "),
            ("Evaluate ", "How did you evaluate "),
            ("Test ", "How did you test "),
            ("Compare ", "How did you compare "),
            ("Measure ", "How did you measure "),
            ("Optimize ", "How did you optimize "),
            ("Perform ", "How did you perform "),
            ("Add ", "How did you add "),
            ("Expose ", "How did you expose "),
            ("Secure ", "How did you secure "),
            ("Protect ", "How did you protect "),
        )
        for prefix, replacement in mapping:
            if objective.startswith(prefix):
                return replacement + objective[len(prefix) :].lower().lstrip()
        return objective[0].upper() + objective[1:]

    def _phase_for(self, question_index: int) -> str:
        for phase, (lo, hi) in PHASES.items():
            if lo <= question_index <= hi:
                return phase
        return "wrapup"

    # -- completion ---------------------------------------------------------

    def _wrap_up(self, state: InterviewState, reason: str) -> EngineTurn:
        state.status = "completed"
        state.phase = "wrapup"
        state.completed_reason = reason
        feedback = self._build_feedback(state)
        state.report = feedback
        state.transcript.append(
            TranscriptEntry(role="interviewer", text="Interview completed.")
        )
        return EngineTurn(reply="Interview completed.", done=True, feedback=feedback)

    def _build_feedback(self, state: InterviewState) -> Feedback:
        """Deterministic, honest M1 feedback from measurable signals only.
        The RAG-grounded Grader + Reporter (M2-M4) replace the heuristics."""
        n = len(state.asked)
        covered = len(state.covered_days)
        early = state.completed_reason in {None, ""} or (
            len(state.asked) < self.default_questions
        )
        answers = [
            t.text for t in state.transcript if t.role == "candidate"
        ]
        avg_len = sum(len(a) for a in answers) / max(len(answers), 1)

        summary = (
            f"Practice interview completed after {n} questions across {covered} "
            f"curriculum days."
        )
        strengths = ["Engaged with every question asked."]
        if avg_len >= 120:
            strengths.append("Provided detailed, substantive answers.")
        gaps: list[str] = []
        if early:
            gaps.append(
                "The interview was ended before the full question plan — a full "
                "run gives a more reliable assessment."
            )
        if avg_len < 60:
            gaps.append(
                "Answers were on the shorter side — expand with your reasoning "
                "and the engineering decisions behind each answer."
            )
        if not gaps:
            gaps.append(
                "Deeper per-topic assessment needs a longer run — aim for the "
                "full question sequence next time."
            )
        next_steps = [
            "Revisit your cohort notes on the days covered in this run.",
            "Run another practice interview to broaden topic coverage.",
            "Rehearse explaining each mission in terms of the decisions you made and what you would improve.",
        ]
        return Feedback(
            summary=summary, strengths=strengths, gaps=gaps, next=next_steps
        )
