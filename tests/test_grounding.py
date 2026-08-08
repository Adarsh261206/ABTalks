"""M4 tests: the Grounded Evaluation Engine.

Covers the deterministic retrieval layer (day-exact + topic), concept
grounding (expected/detected/missing), evidence bundles on every grade,
explicit low-confidence handling, missing/ambiguous curriculum, grounded
follow-up targets, engine reasoning metadata, and evidence-backed reports.
No regressions: the full M1-M3 suite must stay green.
"""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from app.agents.grader import GradeResult, Grader, build_probe_target
from app.core.agent_engine import AgenticInterviewEngine
from app.core.curriculum import load_curriculum
from app.core.grounding import EvidenceBundle, ground_answer
from app.core.llm import LLMGateway
from app.core.profile import analyze_profile
from app.core.retrieval import CurriculumIndex, retrieve_day
from app.domain.candidate import CandidateProfile, Member, Mission, Signals
from app.domain.interview import InterviewState, Question
from app.infrastructure.llm import LLMError
from app.infrastructure.llm_mock import MockLLMProvider

CURRICULUM = load_curriculum()


def _run(coro):
    return asyncio.run(coro)


def _candidate(
    missions: list[dict] | None = None,
    role: str = "Software Engineer",
    years: int = 3,
) -> CandidateProfile:
    return CandidateProfile(
        member=Member(id="C1", name="Test Candidate", jobRole=role, yearsExperience=years),
        missions=[Mission(**m) for m in (missions or [])],
    )


GERALD = _candidate(
    missions=[
        {"day": 7, "title": "A", "passed": True, "attempts": 5},
        {"day": 8, "title": "B", "passed": False, "attempts": 4},
        {"day": 10, "title": "C", "passed": False, "attempts": 3},
        {"day": 12, "title": "D", "passed": True, "attempts": 1},
        {"day": 22, "title": "E", "passed": False, "attempts": 2},
    ],
    role="IT Support Specialist",
    years=20,
)


async def _no_sleep(_seconds: float) -> None:
    return None


def _new_state() -> InterviewState:
    return InterviewState(session_id="s1")


class CapturingStructuredProvider:
    """Captures the user prompt so tests can assert grounding content."""

    name = "capture"

    def __init__(self, structured: list[dict]) -> None:
        self._structured = list(structured)
        self.messages: list[dict] = []

    async def chat(self, messages, temperature=0.2, max_tokens=None) -> str:
        raise LLMError("no chat needed")

    async def structured(self, messages, schema: type[BaseModel], temperature=0.0) -> BaseModel:
        self.messages = list(messages)
        return schema.model_validate(self._structured.pop(0))


# ------------------------------------------------------------- retrieval

def test_retrieval_day_exact_returns_smallest_evidence():
    result = retrieve_day(CURRICULUM, 7)
    assert result.day == 7
    assert result.confidence == 1.0
    kinds = [c.kind for c in result.chunks]
    assert kinds.count("objective") == 2  # smallest units, capped
    assert any(c.kind == "tool" and "Sentence Transformers" in c.text for c in result.chunks)
    assert "embeddings" in result.concepts


def test_retrieval_modules_mapped_from_json():
    assert CURRICULUM[7].module == "Embeddings & Vector Search"
    assert CURRICULUM[12].module == "LLM Core, Prompting & Fine-Tuning"
    assert CURRICULUM[22].module == "Agentic AI & MCP"


def test_retrieval_day_missing_curriculum_explicit():
    result = retrieve_day({}, 7)
    assert result.day == 7
    assert result.confidence == 0.0
    assert "ungrounded" in result.note


def test_retrieval_topic_finds_embedding_day():
    index = CurriculumIndex(CURRICULUM)
    result = index.retrieve_topic("how are text chunks converted into vector embeddings")
    assert result.day == 7
    assert result.ambiguous is False
    assert result.module == "Embeddings & Vector Search"


def test_retrieval_topic_ambiguous_when_days_tie():
    index = CurriculumIndex(CURRICULUM)
    result = index.retrieve_topic("install and configure")
    assert result.ambiguous is True
    assert result.day in (1, 2)


def test_retrieval_topic_no_match_zero_confidence():
    index = CurriculumIndex(CURRICULUM)
    result = index.retrieve_topic("zzzzz qqqqq")
    assert result.day is None
    assert result.confidence == 0.0
    assert result.ambiguous is True


def test_retrieval_topic_empty_query_ambiguous():
    index = CurriculumIndex(CURRICULUM)
    result = index.retrieve_topic("yes")
    assert result.confidence == 0.0
    assert result.ambiguous is True


# ------------------------------------------------------------- grounding

def test_grounding_detects_expected_and_missing_concepts():
    g = ground_answer(
        7, CURRICULUM[7],
        "I generated embeddings for every knowledge base chunk using sentence transformers",
    )
    assert g.curriculum_day == 7
    assert g.module == "Embeddings & Vector Search"
    assert g.learning_objective
    assert g.concepts_expected
    assert set(g.concepts_detected) <= set(g.concepts_expected)
    assert g.concepts_missing == [
        c for c in g.concepts_expected if c not in g.concepts_detected
    ]
    assert any("sentence transformers" in c.lower() for c in g.concepts_detected)
    assert g.retrieved_chunks
    assert g.retrieved_chunks[0].kind == "objective"


def test_grounding_retrieval_confidence_high_and_low():
    low = ground_answer(7, CURRICULUM[7], "yes")
    assert low.retrieval_confidence == 0.4
    assert low.concepts_detected == []
    assert "Low retrieval confidence" in low.note
    high = ground_answer(
        7, CURRICULUM[7],
        "I generated embeddings for knowledge base chunks using sentence transformers",
    )
    assert high.retrieval_confidence > 0.7
    assert high.grading_confidence > 0.5
    assert "Low retrieval confidence" not in high.note


def test_grounding_missing_curriculum_is_explicit():
    g = ground_answer(7, None, "I did everything")
    assert g.curriculum_day == 7
    assert g.retrieval_confidence == 0.0
    assert g.grading_confidence == 0.0
    assert "ungrounded" in g.note
    g2 = ground_answer(None, None, "I did everything")
    assert g2.retrieval_confidence == 0.0


def test_grounding_objective_selected_by_answer_overlap():
    g = ground_answer(
        12, CURRICULUM[12],
        "I compared zero-shot and few-shot prompts on a fixed question set",
    )
    assert "zero-shot" in g.learning_objective.lower() or "compare" in g.learning_objective.lower()


# ---------------------------------------------------------------- grader

def test_grader_evidence_bundle_attached_in_fallback():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="q")
        result = await grader.grade(
            q, "I generated embeddings for chunks using sentence transformers", CURRICULUM[7], _candidate()
        )
        assert result.evidence is not None
        assert result.evidence.curriculum_day == 7
        assert result.evidence.concepts_expected
        assert result.evidence.concepts_missing
        assert "Day 7" in result.evidence.reason
        assert "missed" in result.evidence.reason

    _run(_body())


def test_grader_evidence_bundle_attached_in_llm_path():
    async def _body():
        provider = CapturingStructuredProvider(
            [
                {
                    "accuracy": 3.5, "depth": 3.5, "clarity": 3.5, "honesty_bonus": 0.0,
                    "evidence_quotes": [], "mistakes": [], "overclaim": False,
                    "overclaim_evidence": None, "vague": False, "vague_evidence": None,
                }
            ]
        )
        grader = Grader(LLMGateway(primary=provider, sleep=_no_sleep), use_llm=True)
        q = Question(day=7, text="q")
        result = await grader.grade(
            q, "I generated embeddings for chunks using sentence transformers", CURRICULUM[7], _candidate()
        )
        assert result.accuracy == 3.5
        assert result.evidence is not None
        assert result.evidence.retrieval_confidence > 0.6
        prompt = provider.messages[1]["content"]
        assert "Retrieved curriculum evidence" in prompt
        assert "Concepts expected" in prompt
        assert "Concepts missing" in prompt

    _run(_body())


def test_grader_grounded_accuracy_penalizes_uncovered_concepts():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="q")
        terse = await grader.grade(q, "yes", CURRICULUM[7], _candidate())
        detailed = await grader.grade(
            q,
            "I generated embeddings for every knowledge base chunk with sentence "
            "transformers and compared them by vector similarity",
            CURRICULUM[7],
            _candidate(),
        )
        assert terse.evidence.concepts_detected == []
        assert terse.accuracy < 3.0
        assert detailed.accuracy > terse.accuracy
        assert detailed.weighted_score > terse.weighted_score
        assert "no expected concepts detected" in terse.evidence.reason

    _run(_body())


def test_grader_ungrounded_reason_when_curriculum_missing():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=99, text="q")
        result = await grader.grade(q, "some answer", None, _candidate())
        assert result.evidence is not None
        assert result.evidence.retrieval_confidence == 0.0
        assert "ungrounded" in result.evidence.reason
        assert 1.0 <= result.accuracy <= 5.0

    _run(_body())


# -------------------------------------------------------- follow-up engine

def test_followup_probes_missing_concept_from_retrieved_objective():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=8, text="q")
        result = await grader.grade(
            q, "I set up a database for the project", CURRICULUM[8], GERALD
        )
        target = build_probe_target(result, "I set up a database for the project", 8)
        assert target.kind == "probe"
        assert target.target in result.evidence.concepts_missing
        assert "missed concept" in target.followup_reason
        assert target.objective == result.evidence.learning_objective

    _run(_body())


def test_followup_challenges_mistake_before_missing_concepts():
    bundle = EvidenceBundle(
        curriculum_day=7,
        concepts_expected=["a", "b"],
        concepts_detected=[],
        concepts_missing=["a", "b"],
    )
    grade = GradeResult(
        day=7, accuracy=2.0, depth=2.0, clarity=2.0,
        mistakes=["claims embeddings are lossless"], evidence=bundle,
    )
    target = build_probe_target(grade, "answer text", 7)
    assert target.kind == "challenge"
    assert target.target == "claims embeddings are lossless"


def test_followup_deepens_when_all_concepts_covered():
    bundle = EvidenceBundle(
        curriculum_day=7,
        concepts_expected=["a"],
        concepts_detected=["a"],
        concepts_missing=[],
    )
    grade = GradeResult(
        day=7, accuracy=4.5, depth=4.5, clarity=4.0, evidence=bundle,
    )
    target = build_probe_target(grade, "I covered the full pipeline", 7)
    assert target.kind == "deepen"
    assert target.followup_reason.startswith("mastery demonstrated")


# ------------------------------------------------- engine metadata

def test_engine_records_reasoning_metadata_per_answer():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        await engine.process(state, "yes")  # first turn: question asked, no grade
        await engine.process(state, "yes")  # terse -> graded + follow-up
        await engine.process(
            state,
            "I generated embeddings for knowledge base chunks using sentence transformers",
        )
        reasoning = state.meta["reasoning"]
        assert len(reasoning) == 2
        entry = reasoning[0]
        required = {
            "curriculum_day", "module", "learning_objective", "retrieved_chunks",
            "retrieval_confidence", "grading_confidence", "concepts_expected",
            "concepts_detected", "concepts_missing", "followup_reason", "mastery_delta",
        }
        assert required <= set(entry)
        assert entry["curriculum_day"] == 12  # GERALD's warm-up = highest-prior completed day
        assert entry["retrieval_confidence"] == 0.4
        assert entry["mastery_delta"] is not None
        assert entry["followup_reason"]  # follow-up fired on the terse answer
        assert state.meta["day_evidence"]["12"]["missing"]
        assert state.meta["last_grade"]["grading_confidence"] >= 0.0

    _run(_body())


def test_engine_followup_transcript_carries_grounding_meta():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        await engine.process(state, "yes")
        await engine.process(state, "yes")
        entry = next(t for t in state.transcript if t.role == "interviewer" and t.meta.get("action") == "follow_up")
        assert entry.meta["kind"] == "probe"
        assert entry.meta["missing_concepts"]

    _run(_body())


def test_reporter_fallback_cites_retrieved_evidence():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, _candidate(
            [{"day": d, "title": f"D{d}", "passed": True, "attempts": 1}
             for d in (7, 8, 10, 12, 16, 22, 23, 28, 29, 31)]
        ))
        done = None
        for i in range(9):
            turn = await engine.process(
                state, f"Answer {i} with enough detail to show reasoning about architecture choices."
            )
            if turn.done:
                done = turn
                break
        assert done is not None
        fb = done.feedback
        assert any("missing" in g for g in fb.gaps)
        assert any("expected" in g for g in fb.gaps)

    _run(_body())


def test_reporter_llm_prompt_includes_grounded_evidence():
    async def _body():
        provider = CapturingStructuredProvider(
            [
                {
                    "summary": "Practice interview completed. Strong session.",
                    "strengths": [], "gaps": [], "next": [],
                }
            ]
        )
        from app.agents.reporter import Reporter

        reporter = Reporter(LLMGateway(primary=provider, sleep=_no_sleep), use_llm=True)
        state = _new_state()
        state.belief = {"7": [4.0]}
        state.covered_days = [7]
        state.asked = [Question(day=7, text="q")]
        state.meta["day_evidence"] = {
            "7": {
                "objective": "Generate embeddings for every knowledge base chunk",
                "detected": ["embeddings"], "missing": ["chunk"],
                "retrieval_confidence": 0.8, "score": 4.0,
            }
        }
        fb = await reporter.report(state, analyze_profile(GERALD), CURRICULUM)
        assert fb.summary == "Practice interview completed. Strong session."
        prompt = provider.messages[1]["content"]
        assert "Per-day grounded evidence" in prompt
        assert "Generate embeddings" in prompt

    _run(_body())
