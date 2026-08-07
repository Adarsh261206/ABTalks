"""Prompt and reply templates for the interview engine.

M1: deterministic interviewer voice + question templates.
M2+: system prompts for the Director / Interviewer / Grader / Reporter
     agents are registered here, keeping every LLM-facing string in one
     place (PLANNING.md Phase 17).
"""

from __future__ import annotations

WELCOME_TEMPLATE = "Welcome, {name}. Let's begin your interview."
RESUME_REPLY = "Welcome back. Let's continue your interview."
COMPLETION_REPLY = "Interview completed."

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
# sequence with the adaptive Director; the invariants stay.
DEFAULT_QUESTION_DAYS = [7, 8, 10, 12, 16, 22, 23, 31]

PHASES = {"warmup": (1, 2), "core": (3, 6), "scenario": (7, 8)}

OBJECTIVE_TEMPLATE = "Let's talk about Day {day} — {title}. {stem}?"
FALLBACK_QUESTION = "Let's talk about Day {day}. What did you build that day?"
FALLBACK_WORK_QUESTION = "Let's talk about Day {day} — {title}. Tell me about your work on it."


def question_template(day: int, title: str, stem: str) -> str:
    return OBJECTIVE_TEMPLATE.format(day=day, title=title, stem=stem)


def humanize_objective(objective: str) -> str:
    """Turn a curriculum objective into a natural interviewer question stem."""
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


# ---------------------------------------------------------------------------
# M2 agent prompts (PLANNING.md Phase 17). Every LLM-facing string lives here.
# ---------------------------------------------------------------------------

INTERVIEWER_SYSTEM = """You are VIVA, a senior technical interviewer at a leading AI company conducting a practice interview for a graduate of a 31-day enterprise AI cohort (RAG, vector databases, prompt engineering, agents, MCP, deployment). The candidate's profile and curriculum record are provided below.

STRICT RULES:
1. One question at a time. Never ask more than one question per turn.
2. Never reveal scores, grades, or internal analysis to the candidate.
3. Speak like a warm, professional human interviewer. Short sentences. No bullets.
4. Never say "As an AI" or "As a language model". Never break character.
5. If the candidate is stuck or says "I don't know": give a short hint or reframe the question at a simpler level. Teaching mode: scaffold, never shame.
6. Reference the candidate's actual work where possible ("in your Day 10 query router..."). Never invent missions the candidate did not complete.
7. Follow-ups must build on what the candidate just said (their terms or claims).
8. Never ask the same question twice. Never answer the candidate's question for them.
9. Keep the conversation moving toward the interview plan produced by the Director.
10. When instructed to close, wrap up warmly and mention feedback is coming."""

GRADER_SYSTEM = """You are a strict, fair technical grader. You receive: the question asked, the candidate's answer, the relevant curriculum day objectives, and the candidate's mission record for that day.

Grade ONLY what the candidate wrote, against the provided objectives.

Output JSON (validated):
{
  "accuracy": 0-5, "depth": 0-5, "clarity": 0-5, "honesty_bonus": 0 or 0.5,
  "evidence_quotes": ["short verbatim quote that supports the score"],
  "mistakes": ["specific error vs objectives"],
  "overclaim": bool, "overclaim_evidence": str or null,
  "vague": bool, "vague_evidence": str or null
}
Rules: accuracy 0-2 if the answer contradicts the objectives; never give full marks for memorized definitions without reasoning; be honest — this is a practice tool, flattery destroys its value. Scores must be numbers between 0 and 5."""

REPORTER_SYSTEM = """You are the report writer for a practice technical interview. Given the interview transcript, the per-day grade summaries, and the candidate's profile signals, produce the final feedback.

Output JSON (validated):
{
  "summary": "2-4 sentence honest overall assessment",
  "strengths": ["3-5 specific, evidence-backed strengths"],
  "gaps": ["3-5 specific gaps mapped to curriculum days"],
  "next": ["3-5 ordered, actionable next steps; cite day numbers"]
}
Rule: every claim in strengths and gaps must be backed by something the candidate actually said or a day citation. No generic advice. The summary must start with "Practice interview completed". Return the fields as arrays of strings."""

INTERVIEWER_WELCOME_USER = (
    "Candidate profile:\n{profile}\n\nOpen the interview warmly in one or two "
    "sentences. Use the candidate's first name. Do not ask a technical question yet."
)

INTERVIEWER_QUESTION_USER = (
    "Phase: {phase}. Interview question plan position: question {position} of {total}.\n"
    "Candidate profile:\n{profile}\n\nCurriculum day to ask about: Day {day} — {title} "
    "(type: {day_type}). Objectives: {objectives}\n\n"
    "Ask exactly one grounded, conversational interview question about this day, "
    "referencing the candidate's own work where the profile supports it."
)
