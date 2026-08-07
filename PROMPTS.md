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

### 2026-08-07 ~21:45 IST — Senior Refactor (pre-M2 debt reduction)

**Prompt:** "Before implementing Milestone 2, perform a senior engineering refactor. Reduce future technical debt by extracting interfaces, services, providers, repositories, prompts, and domain models. Do not change functionality. Do not add new features. Preserve all passing tests. The objective is to make the codebase capable of supporting the remaining milestones without requiring major rewrites."

**What the AI did (behavior-preserving, zero new features):**
- **Domain models** → `app/domain/`: `candidate.py` (CandidateProfile/Member/Mission/Signals), `interview.py` (InterviewState/TranscriptEntry/Question/EngineTurn/Feedback); `schemas.py` is now a pure API boundary re-exporting domain models
- **Repositories** → `app/state/`: `repository.py` (SessionRepository Protocol + StoredSession row), `store.py` (SqliteSessionStore), `memory_store.py` (InMemorySessionStore for tests/mock mode), `serialization.py` (domain↔row mapping, single place)
- **Services** → `app/services/`: `interview.py` (InterviewService use-case with domain errors SessionNotFound/Expired/Completed), `ratelimit.py` (RateLimiter, clock-injectable, RateLimitExceeded), `locks.py` (SessionLockRegistry)
- **Providers** → `app/infrastructure/`: `llm.py` (LLMProvider Protocol), `llm_client.py` (OpenAICompatibleProvider + schema-JSON parser), `llm_mock.py` (MockLLMProvider, schema-shaped deterministic output)
- **Gateway** → `app/core/llm.py` (LLMGateway: retry w/ backoff → schema re-prompt loop → fallback provider; per PLANNING.md Phase 11 ladder)
- **Prompts** → `app/core/prompts.py` (all interviewer strings/templates/humanize/END_KEYWORDS in one registry for M2 agent prompts)
- **Curriculum** → `app/core/curriculum.py` (DayInfo + loader; M4 retrieval source)
- **Routes** are now thin (HTTP parsing + status mapping only); `main.py` is the composition root wiring store/engine/services/providers into `app.state`; engine unchanged in behavior
- Fixed during review: mock schema builder broke on required `Field(...)` fields (PydanticUndefined), test sleep lambda not awaitable, removed `__import__` hacks, pyproject switched to package discovery (`app*`), openai dep added

**Outcome:** 24 original contract tests + 13 new layer tests = **37/37 green**; live smoke test confirms identical behavior (humanized questions, 8-question completion, 409-with-report). Committed & pushed.

---

### 2026-08-07 ~22:30 IST — Milestone 2 (Interview core v1: profile analyzer + Director/Interviewer/Grader/Reporter agents)

**Prompt:** "Milestone 1 is frozen. Begin Milestone 2 exactly as defined in the roadmap: single-agent loop that satisfies minimums (8 Qs, 4 days, welcome, wrap-up, feedback shape) — profile analyzer, Director (invariants in code), Interviewer voice prompt, simple grader (no RAG yet), Reporter v1, LLM gateway with retries + mock. Preserve all 37 tests; no architecture changes; commit + push."

**What the AI did (M2 — Interview core v1):**
- **`app/core/profile.py`** — deterministic profile analyzer: per-day mastery priors (0-1) from attempts/first-try rate/skips/failures/seniority (per PLANNING 17.8: skipped→0.2, failed→0.3, passed 0.7 minus attempt penalty), `probe_days` (failed/skipped/≥4-attempt), `profile_type` (strong/grinder/struggling/non_technical/average)
- **`app/agents/director.py`** — Director: code-enforced invariants (≥8 Qs, ≥4 distinct days, no repeats till plan exhausted), profile-aware plan (warm-up Day 7 → probe days pulled forward → remaining core → extra days); wrap gating stays in engine
- **`app/agents/interviewer.py`** — Interviewer: renders welcome/questions in VIVA voice (LLM mode, prompt per PLANNING 17.1) with M1 template fallback (question_template + humanize_objective)
- **`app/agents/grader.py`** — Grader v1 (no RAG): rubric 0.5·accuracy + 0.3·depth + 0.2·clarity + honesty bonus (PLANNING 9.12), overclaim/vague flags vs mission record, evidence quotes; LLM structured output (17.3 schema) with deterministic heuristic fallback
- **`app/agents/reporter.py`** — Reporter v1: spec feedback {summary, strengths, gaps, next} from grade averages + probe days + early-end handling; LLM (17.5) with deterministic fallback; empty LLM lists back-filled (edge case 93)
- **`app/core/agent_engine.py`** — `AgenticInterviewEngine`: same start/process contract as M1 engine (async; service layer gained a 2-line `isawaitable` bridge so the M1 engine path is untouched); grades land in `state.belief[day]`; wrap at ≥8 questions / end-keywords / max_turns
- **`app/main.py`** — default engine now the agentic one, wired to the existing LLM gateway (mock provider ⇒ deterministic offline mode via new `uses_mock_primary` flag on the gateway)
- **`tests/test_agents.py`** — 30 new tests (profile math, director invariants, grader heuristics + LLM path + fallback, interviewer, reporter, full engine loops incl. LLM-scripted run and total provider outage)
- Verified: 67/67 tests green (also under `--import-mode=importlib` and runtime-deps-only env); live curl run of Gerald (CAND-010) shows probe days (8/10/22) pulled forward and unprobed failed days (27/28) cited in feedback gaps/next

**Outcome:** Full mock + real-LLM interview loop; 67/67 green; live smoke test passes. Committed & pushed.

---

### 2026-08-07 ~22:00 IST — Milestone 3 (Multi-agent upgrade: belief state + follow-ups + hints)

**Prompt:** "haa karde commit" (continuing the M3 execution thread — the milestone brief: belief state, adaptation, follow-ups, honesty; follow-up depth cap; hints when stuck; keep all M1/M2 contracts intact).

**What the AI did (M3 — Multi-agent upgrade):**
- **`app/core/belief.py`** — belief state: per-day mastery blend (0.7·prior + 0.3·live), confidence growth, difficulty tiers (L1/L2/L3) with seniority bias and recent-score escalation/de-escalation
- **`app/agents/director.py`** — Director now belief-driven: `next_question` picks difficulty from the belief state; `decide()` picks the next action (ask_new / follow_up / hint) deterministically from grade signals (terse/overclaim/vague/mistakes/shallow); follow-up depth cap = 2; invariants (≥8 Qs, ≥4 days, no repeats) still enforced in code
- **`app/agents/grader.py`** — `GradeResult` + `ProbeTarget` + `build_probe_target` (target priority: mistakes > overclaims > vagueness > deepen)
- **`app/agents/interviewer.py`** — `render_followup` + `render_hint` (LLM first, template fallbacks in VIVA voice); new `FOLLOWUP_USER` / `HINT_USER` prompts
- **`app/core/agent_engine.py`** — full M3 loop per turn: grade → belief update → Director decide → Interviewer render; reasoning stored in `state.meta` (recent scores, overclaims, last decision)
- Fixed stale tests (M1-era `next_question(state)` call; outage test turn budget raised for follow-up depth); removed duplicate `_GraderOutput` class
- Verified: 67/67 tests green

**Outcome:** Adaptive, belief-driven interviews with grounded follow-ups and teaching-mode hints. Committed `171c9d3`.

---

### 2026-08-07 ~22:20 IST — Milestone 4 (Grounded Evaluation Engine: RAG + evidence)

**Prompt:** Full M4 brief: "Milestones 1-3 COMPLETE and FROZEN… Your only objective is to make every evaluation, follow-up, and final feedback evidence-based." — deterministic lightweight RAG over curriculum.json, grounding rules (every weak score must explain expected objective / retrieved evidence / what was missed / why score decreased), RAG pipeline, reasoning metadata (curriculum_day, module, learning_objective, retrieved_chunks, retrieval_confidence, grading_confidence, concepts_expected/detected/missing, followup_reason, mastery_delta), evidence engine, follow-up engine (probe missing concepts, never random), no LangChain/LlamaIndex/CrewAI, comprehensive tests, zero regressions.

**What the AI did (M4 — Grounded Evaluation Engine):**
- **`app/core/retrieval.py`** — deterministic RAG layer: `CurriculumIndex` (lexical token index over days), day-exact retrieval returning the smallest useful evidence (individual objectives + tools as chunks), topic retrieval with ambiguity flag (top-2 within 10% → ambiguous), explicit 0-confidence + note for missing curriculum
- **`app/core/grounding.py`** — `ground_answer()`: picks the objective an answer most addresses (token overlap), classifies expected concepts as detected/missing (tools + objective keywords, phrase-level matching), computes retrieval + grading confidence (answer-side coverage × concept recall); `Grounding` → `EvidenceBundle` (adds reason / followup_reason / mastery_delta)
- **`app/agents/grader.py`** — every grade now carries an `EvidenceBundle`: fallback accuracy = 3.0 + 2·(recall − 0.5) (clamped), depth bonus when ≥3 concepts detected; deterministic `reason` for every score (expected / covered / missed / confidence / why score moved); LLM prompt gains `GRADER_EVIDENCE` block (scores must be grounded in retrieved objectives); `build_probe_target` now probes the specific missing concept from the retrieved objective with a `followup_reason` (mistakes > overclaims > missing concepts > vague > deepen)
- **`app/agents/interviewer.py`** — grounded follow-up fallback ("Day N's objective also expects X — walk me through it"); `FOLLOWUP_USER` prompt carries retrieved objective + detected/missing concepts
- **`app/agents/reporter.py`** — evidence-backed fallback (gaps cite expected objective + missing concepts; strengths cite covered concepts) + `REPORTER_EVIDENCE` block in the LLM prompt
- **`app/core/curriculum.py`** — `DayInfo.module` added; module titles mapped from curriculum.json module ranges
- **`app/core/agent_engine.py`** — stores per-answer reasoning metadata (`state.meta["reasoning"]`, capped 12), per-day evidence (`day_evidence`), `mastery_delta` from the belief update, `followup_reason` on follow-up turns
- **`tests/test_grounding.py`** — 22 new tests: retrieval correctness/topic/ambiguity, concept classification, confidence high/low, missing curriculum explicit, LLM-path evidence in prompt, grounded accuracy penalty, follow-up grounding (probe/challenge/deepen priority), engine metadata (all 11 fields), transcript grounding meta, evidence-backed report, reporter LLM prompt
- Verified: 89/89 tests green (67 prior, zero regressions); grounding latency 0.08 ms (pure arithmetic, no new network calls)

**Outcome:** Every score, follow-up and report is now traceable to curriculum evidence; low retrieval confidence is stated explicitly, never hidden. Committed `dd7e214` + pushed.

---

### 2026-08-07 ~23:00 IST — Milestone 5 (Premium Frontend Experience Layer)

**Prompt:** Full M5 brief: "Milestones 1-4 COMPLETE and FROZEN… build the experience layer around the frozen backend." — 3-screen flow (Landing → Interview Room → Engineering Assessment Report), demo personas, all-candidates browser, live progress panel, grounded follow-up chip, hints, /hint + /end commands, resume in-progress sessions, evidence-driven report with verdict + coverage map + print/export, React + Tailwind, quality bar (responsive, dark, a11y, performance, tests), zero backend changes.

**What the AI did (M5 — Frontend experience layer):**
- **`frontend/`** — new Vite + React 18 + TypeScript + Tailwind v4 (@tailwindcss/vite) app; `src/main.tsx` + `src/App.tsx` (HashRouter: `/`, `/interview`, `/report`); dark-only design system in `src/styles/index.css` (ink/aurora/mint tokens, Inter Variable, fade-up/typing/progress-fill keyframes)
- **`src/lib/api.ts`** — typed client over the frozen API contract (POST /api/interview, GET /api/interview/{id}), 429 auto-retry, ApiError with hint/request_id, localStorage session persistence (`viva.session`), `newSessionId()` = `viva-{candidateId}-{base36}`
- **`src/lib/interview.ts` + `interview.test.ts`** — pure analysis helpers: `analyzeTranscript` (question/probe/hint counts, per-day signals, coverage %, grounded follow-up reason, phases), `phaseFor`, `extractDayNumbers`, `verdictFromSummary`, `CORE_DAYS`; 9 vitest tests
- **`src/lib/data.ts`** — curriculum accessors + DEMO_PROFILES (CAND-010 stretch, CAND-001 strong senior, CAND-019 non-technical) over copies of the frozen JSON datasets
- **Pages** — `Landing` (hero, persona picker, all-20 browser with mission heat, how-it-works), `InterviewRoom` (timeline, aria-live announcements, live sidebar: question x/8, phase rail, 8-core-day coverage grid, grounded follow-up card, hint/End, composer with /hint + /end, resume in-progress sessions, auto-start from pending candidate), `Report` (verdict badge, 3 metrics, strengths/gaps/next with Day-highlight chips, module-wise 31-day coverage map, per-day probe table, transcript accordion, print stylesheet)
- **`app/main.py`** — additive: serves `frontend/dist` when present (StaticFiles for /assets + SPA index.html fallback, /api/* excluded); frozen interview logic untouched
- Bug fixes during build: hint entries previously counted as questions in `analyzeTranscript` (fixed + test); auto-start effect wired (interview never began without it); Report candidate name from local session
- Verified: frontend `tsc -b && vite build` clean (229 kB JS, 69.7 kB gzip), 9/9 vitest green, backend 89/89 green with static mount

**Outcome:** Judges-facing demo flows end to end (pick persona → adaptive interview → printable assessment) with zero changes to the frozen backend. Commit pending push.

---

### 2026-08-07 ~23:00 IST — Milestone 6 (Demo Quality & Judge Experience)

**Prompt:** Full M6 brief: "Milestones 1-5 COMPLETE and FROZEN… entirely about demo quality and judge experience" — loading/empty/error/success states, micro animations, keyboard shortcuts, responsive polish, accessibility, demo mode, copywriting, visual consistency, performance, mobile, print polish; no functionality changes, no bundle bloat; verify build/typecheck/tests/backend all green.

**What the AI did (M6 — polish only, no functionality changes):**
- **`Landing.tsx`** — fixed a real routing bug: `window.location.href = "/interview"` broke under HashRouter (path change only, app reloaded to Landing); now `useNavigate()`. Removes the full-page reload, instant transitions
- **`InterviewRoom.tsx`** — `aria-live="polite"` on the timeline + `role="alert"` on the error banner; error banner now surfaces the backend `hint` from `ApiError` (rate-limit messaging); Send button shows "…" while busy; End button is now two-step ("Confirm end?" for 3s, auto-resets) to prevent accidental demo kills; `/` keyboard shortcut focuses the composer (ignored while typing); compact status chips row (Question x/8 · phase · core days) on mobile where the sidebar is hidden; composer footer now advertises the `/` shortcut
- **`Report.tsx`** — loading state upgraded to pulsing logo + `role="status" aria-busy`; probe table gets `overflow-x-auto` + `min-w` (mobile horizontal scroll) and a proper empty-state row; "Export" relabeled "Print"
- **`styles/index.css`** — `prefers-reduced-motion` block (kills all animations/transitions/smooth-scroll for motion-sensitive users); print stylesheet overhaul: all dark surfaces → white, gray text → near-black, accent text darkened for contrast, glow shadows removed, entrance animations disabled (the previous print output had light-gray text on white, nearly unreadable)
- No new dependencies, no new components, no layout redesign; JS bundle +0.37 kB gzip
- Verified: `npm run typecheck` exit 0, `npm run test` 9/9, `npm run build` clean (70.1 kB gzip), backend 89/89 green

**Outcome:** Every screen now handles its in-between states, keyboard users and mobile judges get parity with desktop, print output is a clean white report, and the demo can't be accidentally ended. Commit `81c2e35` + pushed.
