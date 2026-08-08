## Why VIVA?

| Generic AI Interview | VIVA |
|----------------------|------|
| Same questions for everyone | Questions adapt to your learning journey |
| Generic feedback | Evidence-backed engineering assessment |
| Static interview | Belief-state driven interview |
| Opinion-based scoring | Curriculum-grounded evaluation |
| Chat ends with a score | Ends with a shareable engineering report |

---

# VIVA — The Interviewer That Knows What You Built

**Practice interviews that adapt to you — and end with an engineering report backed by evidence, not opinions.**

An evidence-grounded AI interview system for a 31-day enterprise AI engineering cohort (ABTalks Hackathon entry).

> 📸 Screenshot / demo GIF placeholder — Landing → Adaptive Interview → Engineering Report

> 🔗 **Live demo: https://abtalks-production.up.railway.app** — no install, no login, pick a candidate and start an interview.

| ❌ Generic AI Interview | ✅ Curriculum Grounded |
|---|---|
| ❌ Generic Feedback | ✅ Evidence-Based Engineering Assessment |
| ❌ Static Questions | ✅ Adaptive Interview Engine |

---

## The Problem

Learners finish structured programs — bootcamps, cohorts, 31-day roadmaps — and still can't prove what they know.

Current AI interview tools fail because they:

- ❌ Ask the same generic questions ("tell me about yourself") to everyone
- ❌ Grade how you *sound*, not what you *know*
- ❌ Give feedback like "good job" that no one can act on
- ❌ End with a vibe-based score and no evidence

So candidates stay anxious, mentors stay blind, and managers can't trust the result. Nobody can answer the one question that matters: **did you actually cover the curriculum?**

---

## Our Solution

VIVA reads each candidate's mission record from a real 31-day AI-engineering cohort, retrieves the exact curriculum objective behind every question, and runs a live adaptive interview. When a candidate is shaky, VIVA probes the exact concept they missed — and tells them why. When they're stuck, it gives a hint grounded in the day's objective. When they claim something they never covered, it catches the overclaim. At the end, VIVA produces an **Engineering Assessment Report**: verdict, coverage, strengths, gaps, and next steps — every claim tied to a specific cohort day and backed by transcript evidence.

---

## How VIVA Works

```
Candidate
    ↓
Profile Analysis      reads the mission record — what they've done, what's flagged
    ↓
Belief State          running estimate of mastery for every curriculum day
    ↓
Director              decides the next move: new question, probe, or hint
    ↓
Adaptive Question     targets the next uncovered day's learning objective
    ↓
Grader                retrieves the expected concepts and detects what was covered
    ↓
Evidence              structured metadata — missing concepts, confidence scores
    ↓
Engineering Report    strengths, gaps, next steps — every item evidence-backed
```

---

## What Makes VIVA Different

| Dimension | Generic AI Interview Tool | VIVA |
|---|---|---|
| **Question selection** | Random or canned | Picks the next uncovered curriculum day |
| **Difficulty** | Fixed | Driven by the candidate's belief state |
| **Follow-ups** | Generic "tell me more" | Probes the exact missed concept, reason shown |
| **Hints** | Rare or random | Grounded in the day's learning objective |
| **Evidence** | None | Missing concepts + confidence, per answer |
| **Feedback** | "Good job!" | Day-linked strengths and gaps |
| **Report** | A score | Verdict + coverage + next-step plan |
| **Grounding** | LLM vibes | Deterministic retrieval against objectives |
| **Curriculum awareness** | None | Knows all 31 days and the 8 core days |
| **Determinism** | None | Same input → same behavior, fully testable |

---

## Core Innovations

**Belief State**
- **What it is:** a per-day mastery estimate, seeded by the candidate's mission record and updated after every answer.
- **Why it matters:** the interview personalizes within two turns instead of staying generic.
- **How it improves interviews:** difficulty and coverage decisions follow the candidate, not a script.

**Grounded Evaluation**
- **What it is:** every answer is graded against the retrieved curriculum objective via deterministic concept detection.
- **Why it matters:** evaluation is checkable and auditable, not opinion.
- **How it improves interviews:** candidates can see exactly which concept was covered and which was missed.

**Evidence Chain**
- **What it is:** every interview step emits structured metadata — follow-up reasons, missing concepts, retrieval confidence.
- **Why it matters:** the report's claims are derived from this metadata, never from free-text guesses.
- **How it improves interviews:** the transcript itself becomes proof.

**Adaptive Director**
- **What it is:** a decision agent that picks the next action — ask, probe, or hint — with a cap on consecutive probes.
- **Why it matters:** interviews feel steered by an expert, not scripted or random.
- **How it improves interviews:** weak areas get more time; strong candidates are never interrupted.

**Engineering Assessment Report**
- **What it is:** verdict, coverage percentage, strengths, gaps, and next steps, each tied to a specific cohort day.
- **Why it matters:** it's a shareable, printable artifact a mentor or manager can actually use.
- **How it improves interviews:** the outcome of practice is a deliverable, not a dead-end chat.

---

## Demo Flow

What a judge experiences in under 5 minutes:

```
Landing            →  3 demo personas + all 20 real cohort candidates
Candidate          →  mission record loaded, profile analyzed
Interview          →  live conversation, auto-starts on selection
Adaptive questions →  grounded hints and follow-ups with visible reasons
Evidence           →  every turn tagged with concepts + confidence
Engineering Report →  verdict, coverage, gaps, next steps
```

Then: **Copy link** opens the report on any device, **Print** produces a clean artifact, **New interview** restarts the loop. Refresh mid-interview? The session resumes exactly where it left off.

---

## System Architecture

```
┌──────────────────────────────┐
│  Frontend — React 18 + Tailwind v4         Landing → Interview → Report
└──────────────┬───────────────┘
               │  POST /api/interview · GET /api/interview/{id}
┌──────────────▼───────────────┐
│  Backend — FastAPI           │  one process; serves API + SPA
│  ┌────────────────────────┐  │
│  │ Agents                 │  │  Director decides · Grader scores · Interviewer speaks
│  ├────────────────────────┤  │
│  │ Belief State           │  │  per-day mastery + difficulty tiers
│  ├────────────────────────┤  │
│  │ Grounding Layer        │  │  deterministic retrieval + concept detection
│  ├────────────────────────┤  │
│  │ SQLite Store           │  │  sessions survive restarts · TTL · per-session locks
│  └────────────────────────┘  │
└──────────────────────────────┘
```

---

## Engineering Highlights

✅ 89 backend tests — engine decisions, grading, retrieval, edge-case matrix
✅ 9 frontend tests — analysis helpers, deterministic verdict
✅ Deterministic evaluation — same input, same interview, every run
✅ Session recovery — refresh or server restart, interview continues
✅ Shareable report links — no login, works on any device
✅ Offline demo — deterministic mock provider; the demo never dies
✅ FastAPI · React + Tailwind v4 · SQLite · asyncio
✅ 70 kB gzip frontend bundle · 1–6 ms turn latency
✅ Optional real-LLM mode (OpenAI / Groq) with graceful fallbacks

---

## Why Judges Should Care

- **A hiring manager would use this.** The report names the day, the objective, and the missing concepts — a forwardable artifact, not a chat log.
- **A bootcamp would buy this.** Curriculum-aware interviews and printable assessments plug straight into any structured program.
- **Learners benefit immediately.** Grounded hints and follow-ups teach *during* the interview, not just after.
- **Deterministic evidence matters.** Evaluation runs on structured metadata with confidence scores — not an LLM's impression. You can verify the report against the transcript.
- **It's real engineering, not a wrapper.** Frozen milestone architecture, an edge-case matrix, a verbatim AI-usage log, and tests that prove the engine behaves.

> "Generic AI interviews test whether you *sound* confident. VIVA tests whether you *covered the curriculum* — and shows the evidence."

---

## Quick Start

```bash
git clone https://github.com/Adarsh261206/ABTalks.git && cd ABTalks
./run.sh
```

Open `http://localhost:8000`, pick a candidate, start an interview. Done.

**Want it live?** The repo ships a `Dockerfile` + `railway.toml` — deploy to Railway (free): new project → deploy from this GitHub repo → Railway auto-detects the Dockerfile → open the generated `*.up.railway.app` URL. Zero env vars needed (mock provider).

<details>
<summary>Manual start / real-LLM mode (optional)</summary>

```bash
python3 -m venv .venv && ./.venv/bin/pip install -e .
cd frontend && npm install && npm run build && cd ..
./.venv/bin/uvicorn app.main:app
```

Real-LLM mode: `cp .env.example .env`, set `VIVA_LLM_PROVIDER=openai` (or `groq`) + key, restart. Without a key VIVA runs the deterministic mock provider — the demo never dies.

</details>

---

## Repository Structure

```
ABTalks/
├── app/          FastAPI backend — agents, belief state, grounding, SQLite store
├── frontend/     React SPA — Landing, Interview Room, Engineering Report
├── tests/        backend test suite (89)
├── scripts/      production smoke suite + judge simulation harness
├── data/         curriculum + 20 candidate profiles (JSON)
├── PROMPTS.md    verbatim AI-usage audit trail, M0 → M8
├── PRESENTATION.md   90s/3min/5min pitches, judge walkthrough, 60 Q&As
└── FINAL-RELEASE.md  checklists + emergency plans
```

---

## Future Scope

- Voice interview mode with live transcription
- Mentor analytics dashboards over sessions and reports
- Multi-curriculum onboarding — upload any roadmap
- Real-LLM guardrails tuning UI
- Anti-cheat telemetry (response-timing patterns)
