# PROMPTS.md — AI-Usage Log

This log documents every prompt given to AI assistants (opencode + Breeth memory layer) during the ABTalks hackathon build, in chronological order. It exists to prove the build was genuinely vibe-coded.

**Builder:** Adarsh Sharma (solo)
**Event:** ABTalks Hackathon — Fri 7 Aug 2026 8:00 PM IST → Sun 9 Aug 2026 8:00 PM IST

---

## Log

### 2026-08-07 — Repo Setup (pre-kickoff)

**Prompt:** "bhai apne file mai vo prompts.md ya jo bhi kar bhai as they wil track smjha aur ye rha github repo link bhai har ek prompt ke baad update karna jisse unko sab pata chale"

**What the AI did:**
- Created this PROMPTS.md AI-usage log
- Created README.md for the repo
- Initialized a fresh git repo in the project folder (kept separate from the parent Documents repo so the public repo only contains the project)
- Pushed to https://github.com/Adarsh261206/ABTalks

**Outcome:** Repo live at https://github.com/Adarsh261206/ABTalks with submission checklist items 1 (public repo) and 3 (PROMPTS.md) in place.

---

### 2026-08-07 20:40 IST — Problem Statement + 21-Phase Strategy (kickoff)

**Prompt:** Full 21-phase elite-team strategy prompt (challenge understanding, judge psychology, competition analysis, winning strategy, product vision, feature brainstorm + prioritization, AI system design, agent design, data flow, architecture, folder structure, API design, DB design, UX/UI planning, prompt engineering, 100+ edge cases, risk analysis, winning analysis, implementation roadmap) + problem statement "The Interview Agent — Build the interviewer, not the interview" + curriculum.json + candidates.json + technical-spec.md.

**What the AI did:**
- Read and analyzed all three provided resources (curriculum.json — 31 days / 8 modules; candidates.json — 20 candidate profiles; technical-spec.md — POST /api/interview contract)
- Produced PLANNING.md: complete 21-phase Product Requirements + AI System Design document
- Key decisions locked: Strategy B "Mastery-Driven Interview Engine" (multi-agent: Director/Interviewer/Grader/Prober/Reporter; belief-state mastery model from candidate signals; RAG-grounded grading against curriculum objectives; evidence-quoted feedback; SQLite session state; Groq default + OpenAI fallback + mock ladder; React+Vite+Tailwind frontend; cut auth/voice/long-term memory/K8s)
- Product vision: **VIVA** — "The interviewer that knows what you built"
- Roadmap: M0 (done) → M1-M8 over 47h, 6h buffer; edge-case matrix (100+); full prompt library drafted (interviewer/director/grader/prober/reporter/safety/summarizer/profile analyzer)

**Outcome:** PLANNING.md committed — implementation begins at M1.

---

### 2026-08-07 ~21:00 IST — Milestone 1 Execution (API contract + session store)

**Prompt:** Full M1 execution directive (CTO mode): "Build the BEST possible version. Never sacrifice stability for features. No TODOs. Production quality. Milestone by milestone. Deploy early." — execute Milestone 1 only: `POST /api/interview` contract, SQLite session store, error contract, /health, pytest.

**What the AI did:**
- Built `app/` per PLANNING.md folder structure: `config.py` (pydantic-settings, VIVA_ env prefix), `schemas.py` (contract models), `state/store.py` (SQLite WAL store with TTL expiry + restart persistence), `state/models.py` (InterviewState/TranscriptEntry), `core/engine.py` (M1 deterministic interview state machine — 8 grounded questions across core days [7,8,10,12,16,22,23,31], objective→natural-question humanization, end-keywords, honest deterministic feedback), `routes/interview.py` (manual body parsing for exact error contract: 400/404/409/413/415/422/429; per-session async locks; sliding-window rate limiter), `routes/meta.py` (/health, GET session view), `main.py` (app factory, request-ID middleware, normalized error bodies, TTL cleanup task, CORS)
- Wrote 24 contract tests (spec compliance, restart persistence, TTL expiry, rate limiting, request IDs, control-char sanitization, duplicate-start resume, 409-after-completion with report)
- Verified live: uvicorn + curl full cycle; restart preserved session (continued at Day 10, not Day 7); full 8-question interview completed with feedback; session view shows covered days [7,8,10,12,16,22,23,31]
- Fixed during review: FastAPI dependency-injection issue (store/engine via `request.app.state`), HTTPException handler losing headers (Retry-After), feedback summary counting turns instead of questions, awkward "Understand how X?" → "Walk me through how X"

**Outcome:** 24/24 tests green. M1 complete — committed & pushed.

---
