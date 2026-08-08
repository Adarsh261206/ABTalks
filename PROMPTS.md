# PROMPTS.md — AI-Usage Log (Complete Audit Trail)

This log documents every prompt given to AI assistants (opencode + Breeth memory layer) during the ABTalks hackathon build, in chronological order. It exists to prove the build was genuinely built through iterative AI collaboration.

**Builder:** Adarsh Sharma (solo)
**Event:** ABTalks Hackathon — Fri 7 Aug 2026 8:00 PM IST → Sun 9 Aug 2026 8:00 PM IST

## How to read this log

Each entry follows the same journal structure:

- **Exact Prompt(s):** the prompt text exactly as given to the AI. Where the live conversation was recorded in a prior session's log, the verbatim text is quoted and marked *"recorded verbatim in prior log entry"*. Where the exact original is not recoverable from the available conversation history, it is explicitly marked:

  > Exact prompt unavailable from local history.

  and left as a placeholder to be replaced manually. No prompt is ever invented or paraphrased as if it were exact.
- **AI Response Summary:** what the AI did in response.
- **Implementation Result:** the concrete implementation record.
- **Git Commit:** commit hash(es) + timestamp from the repo history.
- **Outcome:** verified result.

---

## Log

### 2026-08-07 ~19:55 IST — Repo Setup (pre-kickoff)

**Exact Prompt(s):**

> recorded verbatim in prior log entry:
>
> "bhai apne file mai vo prompts.md ya jo bhi kar bhai as they wil track smjha aur ye rha github repo link bhai har ek prompt ke baad update karna jisse unko sab pata chale"

**AI Response Summary:** Created the AI-usage log itself, the README, initialized a fresh git repo (separate from the parent Documents repo) and pushed to GitHub.

**Implementation Result:**
- Created this PROMPTS.md AI-usage log
- Created README.md for the repo
- Initialized a fresh git repo in the project folder (kept separate from the parent Documents repo so the public repo only contains the project)
- Pushed to https://github.com/Adarsh261206/ABTalks

**Git Commit:** `4ecf47d` — "first commit: repo setup + AI-usage log (PROMPTS.md)" (2026-08-07 19:55 IST)

**Outcome:** Repo live at https://github.com/Adarsh261206/ABTalks with submission checklist items 1 (public repo) and 3 (PROMPTS.md) in place.

---

### 2026-08-07 20:40 IST — Milestone 0 (Problem Statement + 21-Phase Strategy)

**Exact Prompt(s):**

> Exact prompt unavailable from local history.
>
> Prior log records that the prompt was a full 21-phase elite-team strategy directive covering: challenge understanding, judge psychology, competition analysis, winning strategy, product vision, feature brainstorm + prioritization, AI system design, agent design, data flow, architecture, folder structure, API design, DB design, UX/UI planning, prompt engineering, 100+ edge cases, risk analysis, winning analysis, implementation roadmap — together with the problem statement "The Interview Agent — Build the interviewer, not the interview", `curriculum.json`, `candidates.json` and `technical-spec.md`.

**AI Response Summary:** Read and analyzed all three provided resources (curriculum.json — 31 days / 8 modules; candidates.json — 20 candidate profiles; technical-spec.md — POST /api/interview contract) and produced PLANNING.md.

**Implementation Result:**
- Produced PLANNING.md: complete 21-phase Product Requirements + AI System Design document
- Key decisions locked: Strategy B "Mastery-Driven Interview Engine" (multi-agent: Director/Interviewer/Grader/Prober/Reporter; belief-state mastery model from candidate signals; RAG-grounded grading against curriculum objectives; evidence-quoted feedback; SQLite session state; Groq default + OpenAI fallback + mock ladder; React+Vite+Tailwind frontend; cut auth/voice/long-term memory/K8s)
- Product vision: **VIVA** — "The interviewer that knows what you built"
- Roadmap: M0 (done) → M1-M8 over 47h, 6h buffer; edge-case matrix (100+); full prompt library drafted (interviewer/director/grader/prober/reporter/safety/summarizer/profile analyzer)

**Git Commit:** `ff4fd9e` — "M0: 21-phase strategy + PRD/System Design (PLANNING.md) + provided resources" (2026-08-07 20:40 IST)

**Outcome:** PLANNING.md committed — implementation begins at M1.

---

### 2026-08-07 ~21:05 IST — Milestone 1 Execution (API contract + session store)

**Exact Prompt(s):**

> Exact prompt unavailable from local history.
>
> Prior log records that the prompt was a CTO-mode execution directive whose verbatim core included:
>
> "Build the BEST possible version. Never sacrifice stability for features. No TODOs. Production quality. Milestone by milestone. Deploy early."
>
> — executing Milestone 1 only: `POST /api/interview` contract, SQLite session store, error contract, `/health`, pytest.

**AI Response Summary:** Built the M1 backend to the frozen spec contract, then verified it live end-to-end and fixed defects found during review.

**Implementation Result:**
- Built `app/` per PLANNING.md folder structure: `config.py` (pydantic-settings, VIVA_ env prefix), `schemas.py` (contract models), `state/store.py` (SQLite WAL store with TTL expiry + restart persistence), `state/models.py` (InterviewState/TranscriptEntry), `core/engine.py` (M1 deterministic interview state machine — 8 grounded questions across core days [7,8,10,12,16,22,23,31], objective→natural-question humanization, end-keywords, honest deterministic feedback), `routes/interview.py` (manual body parsing for exact error contract: 400/404/409/413/415/422/429; per-session async locks; sliding-window rate limiter), `routes/meta.py` (/health, GET session view), `main.py` (app factory, request-ID middleware, normalized error bodies, TTL cleanup task, CORS)
- Wrote 24 contract tests (spec compliance, restart persistence, TTL expiry, rate limiting, request IDs, control-char sanitization, duplicate-start resume, 409-after-completion with report)
- Verified live: uvicorn + curl full cycle; restart preserved session (continued at Day 10, not Day 7); full 8-question interview completed with feedback; session view shows covered days [7,8,10,12,16,22,23,31]
- Fixed during review: FastAPI dependency-injection issue (store/engine via `request.app.state`), HTTPException handler losing headers (Retry-After), feedback summary counting turns instead of questions, awkward "Understand how X?" → "Walk me through how X"

**Git Commit:** `0c2ac12` — "M1: API contract + SQLite session store + error contract + 24 tests" (2026-08-07 21:05 IST)

**Outcome:** 24/24 tests green. M1 complete — committed & pushed.

---

### 2026-08-07 ~21:18 IST — Senior Refactor (pre-M2 debt reduction)

**Exact Prompt(s):**

> recorded verbatim in prior log entry:
>
> "Before implementing Milestone 2, perform a senior engineering refactor. Reduce future technical debt by extracting interfaces, services, providers, repositories, prompts, and domain models. Do not change functionality. Do not add new features. Preserve all passing tests. The objective is to make the codebase capable of supporting the remaining milestones without requiring major rewrites."

**AI Response Summary:** Behavior-preserving layered refactor — no new features — so the remaining milestones could build on clean seams.

**Implementation Result (behavior-preserving, zero new features):**
- **Domain models** → `app/domain/`: `candidate.py` (CandidateProfile/Member/Mission/Signals), `interview.py` (InterviewState/TranscriptEntry/Question/EngineTurn/Feedback); `schemas.py` is now a pure API boundary re-exporting domain models
- **Repositories** → `app/state/`: `repository.py` (SessionRepository Protocol + StoredSession row), `store.py` (SqliteSessionStore), `memory_store.py` (InMemorySessionStore for tests/mock mode), `serialization.py` (domain↔row mapping, single place)
- **Services** → `app/services/`: `interview.py` (InterviewService use-case with domain errors SessionNotFound/Expired/Completed), `ratelimit.py` (RateLimiter, clock-injectable, RateLimitExceeded), `locks.py` (SessionLockRegistry)
- **Providers** → `app/infrastructure/`: `llm.py` (LLMProvider Protocol), `llm_client.py` (OpenAICompatibleProvider + schema-JSON parser), `llm_mock.py` (MockLLMProvider, schema-shaped deterministic output)
- **Gateway** → `app/core/llm.py` (LLMGateway: retry w/ backoff → schema re-prompt loop → fallback provider; per PLANNING.md Phase 11 ladder)
- **Prompts** → `app/core/prompts.py` (all interviewer strings/templates/humanize/END_KEYWORDS in one registry for M2 agent prompts)
- **Curriculum** → `app/core/curriculum.py` (DayInfo + loader; M4 retrieval source)
- **Routes** are now thin (HTTP parsing + status mapping only); `main.py` is the composition root wiring store/engine/services/providers into `app.state`; engine unchanged in behavior
- Fixed during review: mock schema builder broke on required `Field(...)` fields (PydanticUndefined), test sleep lambda not awaitable, removed `__import__` hacks, pyproject switched to package discovery (`app*`), openai dep added

**Git Commit:** `15db797` + `b76b452` + `71ce38d` (2026-08-07 21:05–21:18 IST) — "refactor: extract domain/services/infrastructure layers, LLM providers + gateway, prompts registry (behavior-preserving, 37 tests green)" (+ repo hygiene commits)

**Outcome:** 24 original contract tests + 13 new layer tests = **37/37 green**; live smoke test confirms identical behavior (humanized questions, 8-question completion, 409-with-report). Committed & pushed.

---

### 2026-08-07 ~22:00 IST — Milestone 2 (Interview core v1: profile analyzer + Director/Interviewer/Grader/Reporter agents)

**Exact Prompt(s):**

> recorded verbatim in prior log entry:
>
> "Milestone 1 is frozen. Begin Milestone 2 exactly as defined in the roadmap: single-agent loop that satisfies minimums (8 Qs, 4 days, welcome, wrap-up, feedback shape) — profile analyzer, Director (invariants in code), Interviewer voice prompt, simple grader (no RAG yet), Reporter v1, LLM gateway with retries + mock. Preserve all 37 tests; no architecture changes; commit + push."

**AI Response Summary:** Implemented the M2 agentic interview loop per the roadmap, with all invariants code-enforced.

**Implementation Result (M2 — Interview core v1):**
- **`app/core/profile.py`** — deterministic profile analyzer: per-day mastery priors (0-1) from attempts/first-try rate/skips/failures/seniority (per PLANNING 17.8: skipped→0.2, failed→0.3, passed 0.7 minus attempt penalty), `probe_days` (failed/skipped/≥4-attempt), `profile_type` (strong/grinder/struggling/non_technical/average)
- **`app/agents/director.py`** — Director: code-enforced invariants (≥8 Qs, ≥4 distinct days, no repeats till plan exhausted), profile-aware plan (warm-up Day 7 → probe days pulled forward → remaining core → extra days); wrap gating stays in engine
- **`app/agents/interviewer.py`** — Interviewer: renders welcome/questions in VIVA voice (LLM mode, prompt per PLANNING 17.1) with M1 template fallback (question_template + humanize_objective)
- **`app/agents/grader.py`** — Grader v1 (no RAG): rubric 0.5·accuracy + 0.3·depth + 0.2·clarity + honesty bonus (PLANNING 9.12), overclaim/vague flags vs mission record, evidence quotes; LLM structured output (17.3 schema) with deterministic heuristic fallback
- **`app/agents/reporter.py`** — Reporter v1: spec feedback {summary, strengths, gaps, next} from grade averages + probe days + early-end handling; LLM (17.5) with deterministic fallback; empty LLM lists back-filled (edge case 93)
- **`app/core/agent_engine.py`** — `AgenticInterviewEngine`: same start/process contract as M1 engine (async; service layer gained a 2-line `isawaitable` bridge so the M1 engine path is untouched); grades land in `state.belief[day]`; wrap at ≥8 questions / end-keywords / max_turns
- **`app/main.py`** — default engine now the agentic one, wired to the existing LLM gateway (mock provider ⇒ deterministic offline mode via new `uses_mock_primary` flag on the gateway)
- **`tests/test_agents.py`** — 30 new tests (profile math, director invariants, grader heuristics + LLM path + fallback, interviewer, reporter, full engine loops incl. LLM-scripted run and total provider outage)
- Verified: 67/67 tests green (also under `--import-mode=importlib` and runtime-deps-only env); live curl run of Gerald (CAND-010) shows probe days (8/10/22) pulled forward and unprobed failed days (27/28) cited in feedback gaps/next

**Git Commit:** `1a5999c` — "M2: interview core v1 — profile analyzer, Director/Interviewer/Grader/Reporter agents, agentic engine (67 tests green)" (2026-08-07 22:00 IST)

**Outcome:** Full mock + real-LLM interview loop; 67/67 green; live smoke test passes. Committed & pushed.

---

### 2026-08-07 ~22:11 IST — Milestone 3 (Multi-agent upgrade: belief state + follow-ups + hints)

**Exact Prompt(s):**

> Exact prompt unavailable from local history.
>
> Prior log records the milestone brief: belief state, adaptation, follow-ups, honesty; follow-up depth cap; hints when stuck; keep all M1/M2 contracts intact. The short continuation prompt recorded verbatim at the end of the thread:
>
> "haa karde commit"

**AI Response Summary:** Upgraded to a fully adaptive multi-agent loop driven by a per-day belief state with grounded follow-ups and teaching-mode hints.

**Implementation Result (M3 — Multi-agent upgrade):**
- **`app/core/belief.py`** — belief state: per-day mastery blend (0.7·prior + 0.3·live), confidence growth, difficulty tiers (L1/L2/L3) with seniority bias and recent-score escalation/de-escalation
- **`app/agents/director.py`** — Director now belief-driven: `next_question` picks difficulty from the belief state; `decide()` picks the next action (ask_new / follow_up / hint) deterministically from grade signals (terse/overclaim/vague/mistakes/shallow); follow-up depth cap = 2; invariants (≥8 Qs, ≥4 days, no repeats) still enforced in code
- **`app/agents/grader.py`** — `GradeResult` + `ProbeTarget` + `build_probe_target` (target priority: mistakes > overclaims > vagueness > deepen)
- **`app/agents/interviewer.py`** — `render_followup` + `render_hint` (LLM first, template fallbacks in VIVA voice); new `FOLLOWUP_USER` / `HINT_USER` prompts
- **`app/core/agent_engine.py`** — full M3 loop per turn: grade → belief update → Director decide → Interviewer render; reasoning stored in `state.meta` (recent scores, overclaims, last decision)
- Fixed stale tests (M1-era `next_question(state)` call; outage test turn budget raised for follow-up depth); removed duplicate `_GraderOutput` class
- Verified: 67/67 tests green

**Git Commit:** `171c9d3` — "M3: multi-agent upgrade — belief state, follow-up/hint engine, agentic grading loop (67 tests green)" (2026-08-07 22:11 IST)

**Outcome:** Adaptive, belief-driven interviews with grounded follow-ups and teaching-mode hints. Committed `171c9d3`.

---

### 2026-08-07 ~22:21 IST — Milestone 4 (Grounded Evaluation Engine: RAG + evidence)

**Exact Prompt(s):**

> Exact prompt unavailable from local history.
>
> Prior log records that the prompt was the full M4 brief whose verbatim core included:
>
> "Milestones 1-3 COMPLETE and FROZEN… Your only objective is to make every evaluation, follow-up, and final feedback evidence-based."
>
> — deterministic lightweight RAG over curriculum.json, grounding rules (every weak score must explain expected objective / retrieved evidence / what was missed / why score decreased), RAG pipeline, reasoning metadata (curriculum_day, module, learning_objective, retrieved_chunks, retrieval_confidence, grading_confidence, concepts_expected/detected/missing, followup_reason, mastery_delta), evidence engine, follow-up engine (probe missing concepts, never random), no LangChain/LlamaIndex/CrewAI, comprehensive tests, zero regressions.

**AI Response Summary:** Made every evaluation, follow-up and report traceable to curriculum evidence via a deterministic lightweight RAG layer.

**Implementation Result (M4 — Grounded Evaluation Engine):**
- **`app/core/retrieval.py`** — deterministic RAG layer: `CurriculumIndex` (lexical token index over days), day-exact retrieval returning the smallest useful evidence (individual objectives + tools as chunks), topic retrieval with ambiguity flag (top-2 within 10% → ambiguous), explicit 0-confidence + note for missing curriculum
- **`app/core/grounding.py`** — `ground_answer()`: picks the objective an answer most addresses (token overlap), classifies expected concepts as detected/missing (tools + objective keywords, phrase-level matching), computes retrieval + grading confidence (answer-side coverage × concept recall); `Grounding` → `EvidenceBundle` (adds reason / followup_reason / mastery_delta)
- **`app/agents/grader.py`** — every grade now carries an `EvidenceBundle`: fallback accuracy = 3.0 + 2·(recall − 0.5) (clamped), depth bonus when ≥3 concepts detected; deterministic `reason` for every score (expected / covered / missed / confidence / why score moved); LLM prompt gains `GRADER_EVIDENCE` block (scores must be grounded in retrieved objectives); `build_probe_target` now probes the specific missing concept from the retrieved objective with a `followup_reason` (mistakes > overclaims > missing concepts > vague > deepen)
- **`app/agents/interviewer.py`** — grounded follow-up fallback ("Day N's objective also expects X — walk me through it"); `FOLLOWUP_USER` prompt carries retrieved objective + detected/missing concepts
- **`app/agents/reporter.py`** — evidence-backed fallback (gaps cite expected objective + missing concepts; strengths cite covered concepts) + `REPORTER_EVIDENCE` block in the LLM prompt
- **`app/core/curriculum.py`** — `DayInfo.module` added; module titles mapped from curriculum.json module ranges
- **`app/core/agent_engine.py`** — stores per-answer reasoning metadata (`state.meta["reasoning"]`, capped 12), per-day evidence (`day_evidence`), `mastery_delta` from the belief update, `followup_reason` on follow-up turns
- **`tests/test_grounding.py`** — 22 new tests: retrieval correctness/topic/ambiguity, concept classification, confidence high/low, missing curriculum explicit, LLM-path evidence in prompt, grounded accuracy penalty, follow-up grounding (probe/challenge/deepen priority), engine metadata (all 11 fields), transcript grounding meta, evidence-backed report, reporter LLM prompt
- Verified: 89/89 tests green (67 prior, zero regressions); grounding latency 0.08 ms (pure arithmetic, no new network calls)

**Git Commit:** `dd7e214` — "M4: grounded evaluation engine — deterministic curriculum retrieval, evidence-backed grading/follow-ups/reports, reasoning metadata (89 tests green)" (2026-08-07 22:21 IST); followed by `4f77166` (2026-08-07 22:25 IST) "docs: log M3 + M4 prompts in PROMPTS.md (AI-usage log up to date)"

**Outcome:** Every score, follow-up and report is now traceable to curriculum evidence; low retrieval confidence is stated explicitly, never hidden. Committed `dd7e214` + pushed.

---

### 2026-08-07 ~22:41 IST — Milestone 5 (Premium Frontend Experience Layer)

**Exact Prompt(s):**

> Exact prompt unavailable from local history.
>
> Prior log records that the prompt was the full M5 brief whose verbatim core included:
>
> "Milestones 1-4 COMPLETE and FROZEN… build the experience layer around the frozen backend."
>
> — 3-screen flow (Landing → Interview Room → Engineering Assessment Report), demo personas, all-candidates browser, live progress panel, grounded follow-up chip, hints, /hint + /end commands, resume in-progress sessions, evidence-driven report with verdict + coverage map + print/export, React + Tailwind, quality bar (responsive, dark, a11y, performance, tests), zero backend changes.

**Refinement prompt (session resume, same session as completion):**

> verbatim:
>
> "What did we do so far?"

**AI Response Summary:** Built the complete 3-screen frontend experience layer against the frozen backend and verified it end to end.

**Implementation Result (M5 — Frontend experience layer):**
- **`frontend/`** — new Vite + React 18 + TypeScript + Tailwind v4 (@tailwindcss/vite) app; `src/main.tsx` + `src/App.tsx` (HashRouter: `/`, `/interview`, `/report`); dark-only design system in `src/styles/index.css` (ink/aurora/mint tokens, Inter Variable, fade-up/typing/progress-fill keyframes)
- **`src/lib/api.ts`** — typed client over the frozen API contract (POST /api/interview, GET /api/interview/{id}), 429 auto-retry, ApiError with hint/request_id, localStorage session persistence (`viva.session`), `newSessionId()` = `viva-{candidateId}-{base36}`
- **`src/lib/interview.ts` + `interview.test.ts`** — pure analysis helpers: `analyzeTranscript` (question/probe/hint counts, per-day signals, coverage %, grounded follow-up reason, phases), `phaseFor`, `extractDayNumbers`, `verdictFromSummary`, `CORE_DAYS`; 9 vitest tests
- **`src/lib/data.ts`** — curriculum accessors + DEMO_PROFILES (CAND-010 stretch, CAND-001 strong senior, CAND-019 non-technical) over copies of the frozen JSON datasets
- **Pages** — `Landing` (hero, persona picker, all-20 browser with mission heat, how-it-works), `InterviewRoom` (timeline, aria-live announcements, live sidebar: question x/8, phase rail, 8-core-day coverage grid, grounded follow-up card, hint/End, composer with /hint + /end, resume in-progress sessions, auto-start from pending candidate), `Report` (verdict badge, 3 metrics, strengths/gaps/next with Day-highlight chips, module-wise 31-day coverage map, per-day probe table, transcript accordion, print stylesheet)
- **`app/main.py`** — additive: serves `frontend/dist` when present (StaticFiles for /assets + SPA index.html fallback, /api/* excluded); frozen interview logic untouched
- Bug fixes during build: hint entries previously counted as questions in `analyzeTranscript` (fixed + test); auto-start effect wired (interview never began without it); Report candidate name from local session
- Verified: frontend `tsc -b && vite build` clean (229 kB JS, 69.7 kB gzip), 9/9 vitest green, backend 89/89 green with static mount

**Git Commit:** `43382ac` — "M5: premium frontend experience layer — Landing → Interview Room → Engineering Assessment Report (9 vitest green, 89 backend tests green, SPA served from FastAPI)" (2026-08-07 22:41 IST)

**Outcome:** Judges-facing demo flows end to end (pick persona → adaptive interview → printable assessment) with zero changes to the frozen backend. Committed & pushed.

---

### 2026-08-07 ~22:45 IST — Milestone 5A (Frontend foundation verification lock-in)

**Exact Prompt(s):**

> verbatim:
>
> Milestone 5A is complete.
>
> Commit and push the current frontend foundation.
>
> Do not continue implementing more UI.
>
> Do not add additional components.
>
> Do not redesign anything.
>
> Generate:
>
> - npm install works
> - npm run build passes
> - npm run test passes
> - npm run typecheck passes
>
> Fix every issue until all commands succeed.
>
> Commit.
>
> Push.
>
> Only then wait.
>
> Do not begin the remaining frontend screens.

**AI Response Summary:** Re-ran all four verification commands on the existing foundation; all were already green and the working tree was already clean, so no new commit was produced.

**Implementation Result:**
- `npm install` — OK (132 packages, no new dependencies)
- `npm run typecheck` — exit 0
- `npm run test` — 9/9 passed
- `npm run build` — clean (69.76 kB gzip JS)
- `git status` — nothing to commit, working tree clean; local `HEAD` already equal to `origin/main` at `43382ac`

**Git Commit:** none — the foundation was already committed at `43382ac` and pushed; M5A added no changes.

**Outcome:** Frontend foundation verified green across all four commands; repo already in sync with origin.

---

### 2026-08-07 ~22:54 IST — Milestone 6 (Demo Quality & Judge Experience)

**Exact Prompt(s):**

> verbatim:
>
> Milestone 6 begins now.
>
> Milestones 1–5 are COMPLETE and FROZEN.
>
> Do NOT modify backend logic.
>
> Do NOT redesign the frontend.
>
> Do NOT add new AI capabilities.
>
> Do NOT add dashboards, authentication, analytics, voice, or unrelated features.
>
> The product is feature-complete.
>
> Milestone 6 is entirely about demo quality and judge experience.
>
> Your objective is to make every interaction feel polished, intentional, and trustworthy.
>
> Focus only on:
>
> - Loading states
> - Empty states
> - Error states
> - Success states
> - Micro animations
> - Keyboard shortcuts
> - Responsive polish
> - Accessibility improvements
> - Demo mode
> - Copywriting improvements
> - Visual consistency
> - Performance optimization
> - Mobile responsiveness
> - Print report polish
>
> Every change must improve perceived product quality without changing functionality.
>
> Do not add complexity.
>
> Do not increase bundle size unnecessarily.
>
> At completion verify:
>
> - npm run build
> - npm run typecheck
> - npm run test
> - backend tests
>
> All must remain green.
>
> Then provide:
>
> - UX improvements implemented
> - Accessibility improvements
> - Performance improvements
> - Demo improvements
> - Remaining work before submission
> - Suggested commit message
>
> Begin Milestone 6 immediately.

**AI Response Summary:** Polish-only pass — states, keyboard, a11y, mobile parity and print — with no functionality changes.

**Implementation Result (M6 — polish only, no functionality changes):**
- **`Landing.tsx`** — fixed a real routing bug: `window.location.href = "/interview"` broke under HashRouter (path change only, app reloaded to Landing); now `useNavigate()`. Removes the full-page reload, instant transitions
- **`InterviewRoom.tsx`** — `aria-live="polite"` on the timeline + `role="alert"` on the error banner; error banner now surfaces the backend `hint` from `ApiError` (rate-limit messaging); Send button shows "…" while busy; End button is now two-step ("Confirm end?" for 3s, auto-resets) to prevent accidental demo kills; `/` keyboard shortcut focuses the composer (ignored while typing); compact status chips row (Question x/8 · phase · core days) on mobile where the sidebar is hidden; composer footer now advertises the `/` shortcut
- **`Report.tsx`** — loading state upgraded to pulsing logo + `role="status" aria-busy`; probe table gets `overflow-x-auto` + `min-w` (mobile horizontal scroll) and a proper empty-state row; "Export" relabeled "Print"
- **`styles/index.css`** — `prefers-reduced-motion` block (kills all animations/transitions/smooth-scroll for motion-sensitive users); print stylesheet overhaul: all dark surfaces → white, gray text → near-black, accent text darkened for contrast, glow shadows removed, entrance animations disabled (the previous print output had light-gray text on white, nearly unreadable)
- No new dependencies, no new components, no layout redesign; JS bundle +0.37 kB gzip
- Verified: `npm run typecheck` exit 0, `npm run test` 9/9, `npm run build` clean (70.1 kB gzip), backend 89/89 green

**Git Commit:** `77ab92e` — "M6: demo polish — routing fix, a11y (aria-live/reduced-motion), keyboard shortcut, two-step End, print overhaul, mobile chips, empty/loading states" (2026-08-07 22:54 IST)

**Outcome:** Every screen now handles its in-between states, keyboard users and mobile judges get parity with desktop, print output is a clean white report, and the demo can't be accidentally ended. Committed & pushed.

---

### 2026-08-08 ~23:00 IST — Milestone 7 (Judge Review — adversarial self-assessment)

**Exact Prompt(s):**

> verbatim:
>
> Milestone 7 begins now.
>
> Milestones 1–6 are COMPLETE and FROZEN.
>
> Do NOT add features.
>
> Do NOT redesign the UI.
>
> Do NOT modify backend logic.
>
> Do NOT add AI capabilities.
>
> The product is feature complete.
>
> Your job is now completely different.
>
> Act as one of the official hackathon judges.
>
> Imagine you have reviewed 20,000 submissions.
>
> Your objective is NOT to praise this project.
>
> Your objective is to reject it.
>
> Spend as much effort as necessary trying to find weaknesses.
>
> Review every aspect:
>
> - Product originality
> - AI quality
> - UX
> - UI
> - Engineering
> - Architecture
> - Deployment
> - Reliability
> - Edge cases
> - Accessibility
> - Mobile
> - Performance
> - Copywriting
> - Demo experience
> - Judge psychology
> - Innovation
> - Evidence quality
> - Follow-up quality
> - Report quality
> - Visual hierarchy
> - Design consistency
> - Loading experience
> - Empty states
> - Error states
> - Session recovery
> - Candidate experience
>
> For every issue provide:
>
> Severity
>
> Why judges will notice it
>
> Why it matters
>
> Exact fix
>
> Estimated implementation time
>
> Expected impact on final ranking
>
> Do NOT suggest large rewrites.
>
> Only improvements that fit inside the remaining hackathon time.
>
> Rank every recommendation by ROI.
>
> Finally produce:
>
> TOP 10 improvements that would maximize winning probability.
>
> Then STOP.
>
> Do NOT implement anything.
>
> Wait for approval.

**AI Response Summary:** Performed an adversarial judge review grounded in the actual code, found 12 issues (2 critical, 3 high, 7 medium/low) — including the resume-vs-pending race, per-IP rate limit, TBD README, localStorage-hostage report, keyword-verdict contradiction, and scroll-yank — ranked by ROI with a TOP 10 list. No code was changed (per the prompt).

**Implementation Result:** Judge review document delivered in-session (severity / why judges notice / why it matters / exact fix / est. time / ranking impact per issue; ROI table; TOP 10). No files changed.

**Git Commit:** none (review only, per instruction "Do NOT implement anything. Wait for approval.")

**Outcome:** Review recorded; implementation awaited approval.

---

### 2026-08-08 ~23:11 IST — Milestone 7 Implementation (top-6 ROI fixes)

**Exact Prompt(s):**

> verbatim:
>
> Implement ONLY the top 6 highest ROI improvements.
>
> Rules:
>
> - No new features outside the judge review.
> - No architecture changes.
> - No backend redesign.
> - No UI redesign.
> - Preserve all existing functionality.
> - Fix only the highest-impact demo issues.
>
> Priority order:
>
> 1. Resume vs pending candidate race.
> 2. README rewrite.
> 3. Shareable report URLs (/report/:sessionId).
> 4. Deterministic verdict calculation.
> 5. Smart timeline auto-scroll.
> 6. Real LLM verification checklist and README demo guide.
>
> After every fix:
>
> - Run backend tests.
> - Run frontend tests.
> - Run typecheck.
> - Run build.
>
> All must remain green.
>
> Commit after every completed improvement.
>
> Stop after the sixth improvement.

**AI Response Summary:** Implemented each fix in priority order, verifying all four check suites green after every single fix, committing and pushing per fix.

**Implementation Result:**
1. **Resume-vs-pending race** — `InterviewRoom.tsx` never resumes a stale session when a fresh candidate is pending; `Landing.tsx` clears the local session on pick. Verified 89/89 backend, 9/9 frontend, typecheck 0, build clean.
2. **README rewrite** — full README: pitch, architecture diagram, run/test instructions, demo script, LLM verification path.
3. **Shareable report URLs** — `/report/:sessionId` route (plus `/report`), candidate name derived from session id via `candidateById`, Copy link button; `InterviewRoom` now navigates with the session id.
4. **Deterministic verdict** — `verdictFor()` from coverage % + probe count (replaced the prose-keyword `verdictFromSummary`); tests updated.
5. **Smart timeline auto-scroll** — auto-scrolls only when already at the bottom or on first render; never yanks an upward-scrolling judge.
6. **LLM checklist + demo guide** — README gains a scripted demo walkthrough + real-LLM verification checklist (checkbox list) + `.env.example`.

**Git Commit (one per fix):**
- `8f5c7d0` — "M7: fix resume-vs-pending race — pending candidate now always wins, stale local sessions cleared on pick" (23:12)
- `c5cb96e` — "M7: rewrite README — pitch, architecture, run/test instructions, demo script, LLM verification path" (23:12)
- `d1e9314` — "M7: shareable report URLs — /report/:sessionId routes, candidate name from session id, Copy link button" (23:13)
- `8f4ae39` — "M7: deterministic verdict — verdictFor() from coverage+probes, badge can no longer contradict metrics" (2026-08-08 10:05)
- `f3ec661` — "M7: judge-aware timeline scroll — only auto-scroll when at the bottom or on first render" (10:05)
- `caf80c4` — "M7: real-LLM verification checklist + scripted demo guide in README, add .env.example" (10:06)

**Outcome:** All six fixes in, each independently verified green (backend 89/89, frontend 9/9, typecheck exit 0, build clean) and pushed. Frontend JS bundle 70.15 kB gzip.

---

### 2026-08-08 ~10:10 IST — PROMPTS.md audit-trail rebuild (this document)

**Exact Prompt(s):**

> verbatim:
>
> IMPORTANT: This task is NOT about adding new product features.
>
> It is about preserving the complete AI development history for hackathon judging.
>
> The judges will review PROMPTS.md to verify that this project was genuinely AI-assisted.
>
> The current PROMPTS.md contains summaries of prompts.
>
> That is NOT sufficient.
>
> Your task is to rewrite PROMPTS.md so that it becomes a complete chronological AI usage log.
>
> Rules:
>
> 1. Preserve every milestone (M0, M1, M2, M3, M4, M5, M6).
> 2. For EVERY milestone include the COMPLETE ORIGINAL PROMPT exactly as it was given to the AI.
> 3. Do NOT summarize prompts.
> 4. Do NOT shorten prompts.
> 5. Do NOT paraphrase prompts.
> 6. Preserve formatting exactly:
>    - headings
>    - markdown
>    - code blocks
>    - numbered lists
>    - separators
>    - spacing
> 7. If the prompt was written over multiple messages, reconstruct it exactly in chronological order.
> 8. If multiple prompts were given during the same milestone (initial prompt + refinement prompt + stabilization prompt), include ALL of them in sequence.
> 9. Clearly separate:
>    - Exact Prompt(s)
>    - AI Response Summary
>    - Implementation Result
>    - Git Commit (if available)
>    - Outcome
> 10. Every milestone should read like a development journal that a judge can audit.
> 11. Include all execution prompts that drove:
>     - planning
>     - refactoring
>     - stabilization
>     - implementation
>     - grounding
>     - frontend
>     - polish
>     - judge review
> 12. Do NOT omit any prompt simply because it is long.
> 13. Length is not a concern.
> 14. The objective is authenticity and transparency.
> 15. Preserve timestamps wherever available.
> 16. If an exact prompt cannot be reconstructed from available conversation history, explicitly write:
>
> "Exact prompt unavailable from local history."
>
> Never invent or paraphrase an exact prompt.
>
> Instead, leave a placeholder so it can later be replaced manually.
>
> 17. Do NOT modify any implementation history.
> 18. Do NOT modify commits.
> 19. Do NOT modify outcomes.
> 20. The final PROMPTS.md should be a complete audit trail from project initialization to the current milestone.
>
> The resulting document should be something an official hackathon judge can read and confidently conclude that the project was genuinely built through iterative AI collaboration.
>
> Only update PROMPTS.md.
>
> Do not modify any application code.

**AI Response Summary:** Rebuilt PROMPTS.md into this complete chronological audit trail: every milestone (M0 → M7 + M5A) with Exact Prompt(s) (verbatim where available, explicit placeholders where the original is unrecoverable), AI Response Summary, preserved Implementation Result, verified Git Commits from repo history, and Outcome. No application code was modified.

**Implementation Result:** This document.

**Git Commit:** `(this commit)` — "docs: rebuild PROMPTS.md as complete audit-trail AI usage log (exact prompts + placeholders)"

**Outcome:** The log is now an auditable development journal; any remaining gaps (M0/M1/M3-brief/M4/M5 full originals) are explicitly marked for manual replacement rather than invented.
