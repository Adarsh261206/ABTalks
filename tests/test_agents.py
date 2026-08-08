"""M2/M3 tests: profile analyzer, Director invariants, Grader, Interviewer,
Reporter, and the full agentic engine loop (mock + LLM paths)."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from app.agents.director import Director
from app.agents.grader import Grader
from app.agents.interviewer import Interviewer
from app.agents.reporter import Reporter
from app.core.agent_engine import AgenticInterviewEngine
from app.core.belief import init_belief_state
from app.core.curriculum import load_curriculum
from app.core.llm import LLMGateway
from app.core.profile import analyze_profile, prior_for_day
from app.domain.candidate import CandidateProfile, Member, Mission, Signals
from app.domain.interview import Feedback, InterviewState, Question
from app.infrastructure.llm import LLMError
from app.infrastructure.llm_mock import MockLLMProvider

CURRICULUM = load_curriculum()


def _run(coro):
    return asyncio.run(coro)


def _candidate(
    missions: list[dict] | None = None,
    role: str = "Software Engineer",
    years: int = 3,
    signals: Signals | None = None,
) -> CandidateProfile:
    return CandidateProfile(
        member=Member(id="C1", name="Test Candidate", jobRole=role, yearsExperience=years),
        missions=[Mission(**m) for m in (missions or [])],
        signals=signals,
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
    signals=Signals(commitDays=22, missionsCompleted=23, missionsFirstTry=1),
)

# 10 completed curriculum days: the interview pool can support a full
# 8-question run with room to spare (as opposed to GERALD's 2-day pool).
MANY_DAYS = _candidate(
    missions=[
        {"day": d, "title": f"D{d}", "passed": True, "attempts": 1}
        for d in (7, 8, 10, 12, 16, 22, 23, 28, 29, 31)
    ],
    role="Software Engineer",
    years=3,
)


class ScriptedStructuredProvider:
    """LLM provider returning scripted chat text and schema-valid JSON."""

    name = "scripted"

    def __init__(self, chat_replies: list[str], structured: list[dict]) -> None:
        self._chat_replies = list(chat_replies)
        self._structured = list(structured)
        self.chat_calls = 0
        self.structured_calls = 0

    async def chat(self, messages, temperature=0.2, max_tokens=None) -> str:
        self.chat_calls += 1
        return self._chat_replies.pop(0)

    async def structured(self, messages, schema: type[BaseModel], temperature=0.0) -> BaseModel:
        self.structured_calls += 1
        return schema.model_validate(self._structured.pop(0))


class FailingProvider:
    name = "failing"

    async def chat(self, messages, temperature=0.2, max_tokens=None) -> str:
        raise LLMError("provider down")

    async def structured(self, messages, schema: type[BaseModel], temperature=0.0) -> BaseModel:
        raise LLMError("provider down")


async def _no_sleep(_seconds: float) -> None:
    return None


# ------------------------------------------------------------------ profile

def test_profile_failed_and_skipped_days_get_low_priors():
    analysis = analyze_profile(GERALD)
    assert analysis.priors[8] < analysis.priors[7]  # failed < passed
    assert analysis.priors[8] <= 0.45  # 0.3 base + 0.15 seniority cap
    assert analysis.priors[7] >= 0.4
    assert analysis.priors[12] >= 0.6


def test_profile_attempts_penalize_passed_mission_prior():
    low = analyze_profile(_candidate([{"day": 7, "passed": True, "attempts": 6}]))
    high = analyze_profile(_candidate([{"day": 7, "passed": True, "attempts": 1}]))
    assert low.priors[7] < high.priors[7]


def test_profile_seniority_raises_priors():
    junior = analyze_profile(_candidate([{"day": 7, "passed": True, "attempts": 1}], years=1))
    senior = analyze_profile(_candidate([{"day": 7, "passed": True, "attempts": 1}], years=12))
    assert senior.priors[7] > junior.priors[7]


def test_profile_probe_days_from_failures_and_attempts():
    analysis = analyze_profile(GERALD)
    assert 8 in analysis.probe_days
    assert 10 in analysis.probe_days
    assert 22 in analysis.probe_days
    assert 7 in analysis.probe_days  # 5 attempts


def test_profile_missing_mission_treated_as_skipped():
    candidate = _candidate([{"day": 7, "passed": True, "attempts": 1}], role="Analyst")
    assert prior_for_day(candidate, 99) == prior_for_day(candidate, 5) == 0.2
    assert prior_for_day(candidate, 7) > 0.5


def test_profile_classification():
    strong = _candidate(
        [{"day": d, "passed": True, "attempts": 1} for d in range(7, 12)],
        signals=Signals(commitDays=30, missionsCompleted=5, missionsFirstTry=4),
    )
    struggling = _candidate(
        [{"day": 7, "passed": False, "attempts": 5}, {"day": 8, "passed": False, "attempts": 5}],
    )
    non_tech = _candidate([], role="HR Manager", years=10)
    assert analyze_profile(strong).profile_type == "strong"
    assert analyze_profile(struggling).profile_type == "struggling"
    assert analyze_profile(non_tech).profile_type == "non_technical"


# ------------------------------------------------------------------ director

def test_director_plan_pool_is_completed_days_only():
    director = Director(CURRICULUM)
    analysis = analyze_profile(MANY_DAYS)
    plan = director.build_plan(analysis)
    days = [p["day"] for p in plan]
    assert days[0] == 31  # warm-up = highest-prior completed day (ties -> most recent)
    assert len(days) == len(set(days))
    assert len(days) >= 8
    assert set(days) <= set(analysis.completed_days)


def test_director_plan_excludes_uncompleted_and_skipped_days():
    director = Director(CURRICULUM)
    candidate = _candidate(
        missions=[
            {"day": 7, "passed": True, "attempts": 5},
            {"day": 8, "passed": False, "attempts": 4},
            {"day": 10, "passed": False, "attempts": 3},
            {"day": 12, "passed": True, "attempts": 1},
            {"day": 22, "passed": False, "attempts": 2},
            {"day": 29, "skipped": True, "attempts": 0, "passed": False},
        ],
        role="IT Support Specialist",
        years=20,
    )
    analysis = analyze_profile(candidate)
    days = [p["day"] for p in director.build_plan(analysis)]
    assert set(days) == {7, 12}
    assert days[0] == 12  # warm-up = highest-prior completed day
    assert 29 not in days  # skipped: diagnostic-only, never asked


def test_director_plan_orders_struggle_days_before_recent():
    director = Director(CURRICULUM)
    candidate = _candidate(
        missions=[
            {"day": 7, "passed": True, "attempts": 5},   # failed-then-passed, low mastery
            {"day": 8, "passed": True, "attempts": 1},
            {"day": 12, "passed": True, "attempts": 1},
        ],
        role="Software Engineer",
        years=20,
    )
    days = [p["day"] for p in director.build_plan(analyze_profile(candidate))]
    assert days[0] == 12  # warm-up: highest prior (tie -> most recent)
    assert days[1] == 7  # struggle day before the remaining recent day
    assert days[2] == 8


def test_director_never_repeats_until_plan_exhausted():
    director = Director(CURRICULUM)
    analysis = analyze_profile(MANY_DAYS)
    belief = init_belief_state(analysis)
    state = InterviewState(session_id="s")
    state.plan = director.build_plan(analysis)
    asked = []
    while True:
        q = director.next_question(state, analysis, belief, MANY_DAYS)
        if q is None:
            break
        state.asked.append(q)
        state.covered_days.append(q.day)
        asked.append(q.day)
    assert len(asked) == len(set(asked)) == len(state.plan)
    # pool exhausted -> None, and it stays exhausted (no fallback to
    # uncompleted days)
    assert director.next_question(state, analysis, belief, MANY_DAYS) is None


# ------------------------------------------------------------------- grader

def test_grader_fallback_detailed_answer_scores_higher():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="q")
        terse = await grader.grade(q, "yes", CURRICULUM[7], _candidate())
        detailed = await grader.grade(
            q,
            "I built the pipeline step by step: I embedded documents with the day 7 tooling, "
            "set up the vector index, tuned the retriever, and measured recall against a "
            "holdout set before wiring it into the query router.",
            CURRICULUM[7],
            _candidate(),
        )
        assert detailed.weighted_score > terse.weighted_score

    _run(_body())


def test_grader_fallback_honesty_bonus_on_unknown():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="q")
        unsure = await grader.grade(q, "I don't know, I never got that far", CURRICULUM[7], _candidate())
        assert unsure.honesty_bonus == 0.5
        assert unsure.depth <= 2.5

    _run(_body())


def test_grader_fallback_flags_vague_answer():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="q")
        result = await grader.grade(q, "We used stuff like embeddings and things like that", CURRICULUM[7], _candidate())
        assert result.vague is True

    _run(_body())


def test_grader_fallback_detects_overclaim_on_failed_day():
    async def _body():
        grader = Grader(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=8, text="q")
        result = await grader.grade(
            q, "I built the whole retrieval engine and shipped it to production", CURRICULUM[8], GERALD
        )
        assert result.overclaim is True
        assert result.overclaim_evidence

    _run(_body())


def test_grader_uses_llm_output_when_available():
    async def _body():
        provider = ScriptedStructuredProvider(
            chat_replies=[],
            structured=[
                {
                    "accuracy": 4.5,
                    "depth": 4.0,
                    "clarity": 3.5,
                    "honesty_bonus": 0.0,
                    "evidence_quotes": ["tuned the retriever"],
                    "mistakes": [],
                    "overclaim": False,
                    "overclaim_evidence": None,
                    "vague": False,
                    "vague_evidence": None,
                }
            ],
        )
        grader = Grader(LLMGateway(primary=provider, sleep=_no_sleep), use_llm=True)
        q = Question(day=7, text="q")
        result = await grader.grade(q, "some answer", CURRICULUM[7], _candidate())
        assert provider.structured_calls == 1
        assert result.day == 7
        assert result.accuracy == 4.5
        assert result.evidence_quotes == ["tuned the retriever"]

    _run(_body())


def test_grader_falls_back_on_provider_failure():
    async def _body():
        grader = Grader(LLMGateway(primary=FailingProvider(), sleep=_no_sleep), use_llm=True)
        q = Question(day=7, text="q")
        result = await grader.grade(q, "a reasonably detailed answer about the architecture", CURRICULUM[7], _candidate())
        assert 1.0 <= result.accuracy <= 5.0
        assert result.weighted_score > 0

    _run(_body())


# ---------------------------------------------------------------- interviewer

def test_interviewer_llm_renders_question():
    async def _body():
        provider = ScriptedStructuredProvider(
            chat_replies=["So tell me about your Day 7 embedding work."], structured=[]
        )
        interviewer = Interviewer(LLMGateway(primary=provider, sleep=_no_sleep), use_llm=True)
        q = Question(day=7, text="", difficulty="L1", type="concept")
        reply = await interviewer.render_question(q, CURRICULUM[7], _candidate(), "warmup", 1, 8)
        assert provider.chat_calls == 1
        assert "Day 7" in reply

    _run(_body())


def test_interviewer_fallback_question_is_grounded():
    async def _body():
        interviewer = Interviewer(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        q = Question(day=7, text="", difficulty="L1", type="concept")
        reply = await interviewer.render_question(q, CURRICULUM[7], _candidate(), "warmup", 1, 8)
        assert "Day 7" in reply

    _run(_body())


def test_interviewer_falls_back_on_provider_failure():
    async def _body():
        interviewer = Interviewer(LLMGateway(primary=FailingProvider(), sleep=_no_sleep), use_llm=True)
        q = Question(day=7, text="", difficulty="L1", type="concept")
        reply = await interviewer.render_question(q, CURRICULUM[7], _candidate(), "warmup", 1, 8)
        assert "Day 7" in reply

    _run(_body())


# ------------------------------------------------------------------ reporter

def test_reporter_fallback_feedback_shape():
    async def _body():
        reporter = Reporter(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        state = InterviewState(session_id="s")
        state.belief = {"7": [4.2], "8": [2.1], "10": [4.5]}
        state.covered_days = [7, 8, 10]
        state.asked = [Question(day=7, text="q"), Question(day=8, text="q"), Question(day=10, text="q")]
        analysis = analyze_profile(GERALD)
        fb = await reporter.report(state, analysis, CURRICULUM)
        assert isinstance(fb, Feedback)
        assert fb.summary.startswith("Practice interview completed")
        assert fb.strengths and fb.gaps and fb.next

    _run(_body())


def test_reporter_fallback_reflects_grades():
    async def _body():
        reporter = Reporter(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        state = InterviewState(session_id="s")
        state.belief = {"7": [4.5], "8": [1.8]}
        state.covered_days = [7, 8]
        state.asked = [Question(day=7, text="q"), Question(day=8, text="q")]
        fb = await reporter.report(state, analyze_profile(GERALD), CURRICULUM)
        assert any("Day 8" in g for g in fb.gaps)
        assert any("Day 7" in s for s in fb.strengths)

    _run(_body())


def test_reporter_fallback_mentions_unprobed_probe_days():
    async def _body():
        reporter = Reporter(LLMGateway(primary=MockLLMProvider()), use_llm=False)
        state = InterviewState(session_id="s")
        state.belief = {"7": [4.0]}
        state.covered_days = [7]
        state.asked = [Question(day=7, text="q")]
        fb = await reporter.report(state, analyze_profile(GERALD), CURRICULUM)
        assert any("Day 22" in g for g in fb.gaps)

    _run(_body())


def test_reporter_uses_llm_and_fills_empty_lists():
    async def _body():
        provider = ScriptedStructuredProvider(
            chat_replies=[],
            structured=[{"summary": "Practice interview completed. Strong session.", "strengths": [], "gaps": [], "next": []}],
        )
        reporter = Reporter(LLMGateway(primary=provider, sleep=_no_sleep), use_llm=True)
        state = InterviewState(session_id="s")
        state.belief = {"7": [4.5]}
        state.covered_days = [7]
        state.asked = [Question(day=7, text="q")]
        fb = await reporter.report(state, analyze_profile(GERALD), CURRICULUM)
        assert provider.structured_calls == 1
        assert fb.summary == "Practice interview completed. Strong session."
        assert fb.strengths and fb.gaps and fb.next

    _run(_body())


def test_reporter_falls_back_on_provider_failure():
    async def _body():
        reporter = Reporter(LLMGateway(primary=FailingProvider(), sleep=_no_sleep), use_llm=True)
        state = InterviewState(session_id="s")
        state.belief = {"7": [4.5]}
        state.covered_days = [7]
        state.asked = [Question(day=7, text="q")]
        fb = await reporter.report(state, analyze_profile(GERALD), CURRICULUM)
        assert fb.summary.startswith("Practice interview completed")
        assert fb.strengths and fb.gaps and fb.next

    _run(_body())


# -------------------------------------------------------------------- engine

def _new_state() -> InterviewState:
    return InterviewState(session_id="s1")


def test_mock_engine_full_interview_satisfies_minimums():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        welcome = await engine.start(state, MANY_DAYS)
        assert "Test Candidate" in welcome
        done = None
        for i in range(9):
            turn = await engine.process(state, f"Answer {i} with enough detail to show reasoning about architecture choices.")
            if turn.done:
                done = turn
                break
        assert done is not None
        assert len(state.asked) == 8
        assert len(state.covered_days) >= 4
        assert done.feedback is not None
        assert done.feedback.summary.startswith("Practice interview completed")
        assert done.feedback.strengths and done.feedback.gaps and done.feedback.next

    _run(_body())


def test_mock_engine_short_pool_completes_after_pool_exhausted():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        done = None
        for i in range(5):
            turn = await engine.process(state, f"Answer {i} with enough detail to show reasoning about architecture choices.")
            if turn.done:
                done = turn
                break
        assert done is not None
        assert len(state.asked) == 2  # GERALD's pool = {7, 12}, then wrap-up
        assert set(state.covered_days) == {7, 12}
        assert "2 of 2 completed curriculum days" in done.feedback.summary
        assert not any("full question plan" in g for g in done.feedback.gaps)

    _run(_body())


def test_mock_engine_no_completed_days_wraps_immediately():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, _candidate(
            [{"day": 7, "passed": False, "attempts": 5}, {"day": 8, "skipped": True, "attempts": 0, "passed": False}]
        ))
        turn = await engine.process(state, "I have no completed missions.")
        assert turn.done is True
        assert "No completed curriculum days" in turn.feedback.summary

    _run(_body())


def test_mock_engine_first_question_is_warmup_completed_day():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        turn = await engine.process(state, "I built a RAG pipeline.")
        assert "Day 12" in turn.reply  # warm-up = highest-prior completed day

    _run(_body())


def test_mock_engine_records_grades_in_belief():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        await engine.process(state, "A terse yes.")
        await engine.process(state, "Answer two with more detail.")
        assert "12" in state.belief
        assert len(state.belief["12"]) == 1

    _run(_body())


def test_mock_engine_end_keyword_wraps_with_valid_feedback():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM)
        state = _new_state()
        await engine.start(state, GERALD)
        await engine.process(state, "Some answer.")
        turn = await engine.process(state, "end")
        assert turn.done is True
        assert turn.feedback.summary.startswith("Practice interview completed")

    _run(_body())


def test_mock_engine_max_turns_guard():
    async def _body():
        engine = AgenticInterviewEngine(curriculum=CURRICULUM, max_turns=3)
        state = _new_state()
        await engine.start(state, GERALD)
        for _ in range(4):
            turn = await engine.process(state, "Answer")
        assert turn.done is True
        assert state.status == "completed"

    _run(_body())


def test_engine_llm_path_uses_provider():
    async def _body():
        provider = ScriptedStructuredProvider(
            chat_replies=[
                "Welcome, Test Candidate.",
                "Let's talk about Day 31.",
                "Let's talk about Day 7.",
                "Let's talk about Day 8.",
                "Let's talk about Day 10.",
                "Let's talk about Day 12.",
                "Let's talk about Day 16.",
                "Let's talk about Day 22.",
                "Let's talk about Day 23.",
            ],
            structured=[
                {"accuracy": 4.0, "depth": 4.0, "clarity": 4.0, "honesty_bonus": 0.0,
                 "evidence_quotes": [], "mistakes": [], "overclaim": False,
                 "overclaim_evidence": None, "vague": False, "vague_evidence": None}
            ] * 7
            + [
                {"summary": "Practice interview completed. Strong.",
                 "strengths": ["Day 7 solid"], "gaps": ["Day 8 shallow"], "next": ["Revisit Day 8"]}
            ],
        )
        engine = AgenticInterviewEngine(
            curriculum=CURRICULUM, gateway=LLMGateway(primary=provider, sleep=_no_sleep)
        )
        assert engine._gateway.uses_mock_primary is False
        state = _new_state()
        welcome = await engine.start(state, MANY_DAYS)
        assert welcome == "Welcome, Test Candidate."
        done = None
        for i in range(9):
            turn = await engine.process(state, f"Answer {i} in detail about the architecture and trade-offs.")
            if turn.done:
                done = turn
                break
        assert done is not None and done.done is True
        assert done.reply == "Interview completed."
        assert done.feedback.summary == "Practice interview completed. Strong."
        assert provider.structured_calls == 8

    _run(_body())


def test_engine_survives_full_provider_outage():
    async def _body():
        gateway = LLMGateway(primary=FailingProvider(), sleep=_no_sleep)
        engine = AgenticInterviewEngine(curriculum=CURRICULUM, gateway=gateway)
        state = _new_state()
        welcome = await engine.start(state, MANY_DAYS)
        assert "Test Candidate" in welcome
        done = None
        for i in range(40):
            turn = await engine.process(state, f"Answer {i} in detail.")
            if turn.done:
                done = turn
                break
        assert done is not None and done.feedback is not None
        assert len(state.asked) == 8
        assert state.status == "completed"

    _run(_body())
