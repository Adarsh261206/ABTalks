"""Prompt and reply templates for the interview engine.

M1: deterministic interviewer voice + question templates.
M2+: system prompts for Director / Interviewer / Grader / Prober / Reporter
     will be registered here, keeping every LLM-facing string in one place.
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
