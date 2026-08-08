# VIVA — Presentation Package (M8 Phase 5)

**VIVA** = Verbal Intelligent Virtual Assistant for interviews — an adaptive, curriculum-grounded interview agent that turns a 31-day AI-engineering cohort plan into live practice interviews and evidence-grounded engineering assessments.

---

## 1. The 90-Second Pitch

> VIVA is an adaptive interview agent that practices with you — not against you.
>
> Every technical learner has the same problem: you finish a course, you know the material, and then you freeze in the interview. Generic AI interview tools give you generic questions and a vague "you did okay" at the end.
>
> VIVA is different. It starts from a 31-day AI engineering curriculum — real missions, real objectives, real concepts — and runs a live adaptive interview against it. When you're shaky, it asks a grounded follow-up on the exact concept you missed. When you're stuck, it gives you a hint. When you claim something you didn't cover, it catches the overclaim. Every interviewer message carries the curriculum day it targets, and every question is chosen based on a belief state built from your actual answers.
>
> At the end, VIVA produces an Engineering Assessment Report — not a score, but a verdict with strengths, gaps, and a next-step plan, each tied to the specific day and concept it came from. Every claim in the report is backed by transcript evidence. You can copy a link and send the report to a mentor or a judge.
>
> Under the hood it's a grounded evaluation engine: deterministic retrieval, evidence-grounded grading, an agentic director that decides hint, follow-up, or next question, and a belief-state tracker — all running on a frozen, test-covered backend with 89 passing tests and a frontend built like a production SaaS product.
>
> VIVA turns "I finished the course" into "I can prove I know it."

---

## 2. The 3-Minute Pitch

> **The problem.** Learners complete structured programs — bootcamps, cohort plans, 31-day roadmaps — and can't prove what they know. Self-assessments are lying to themselves. Generic AI tools ask generic questions and give generic feedback.
>
> **The insight.** We have structured curricula with explicit learning objectives. If an interview agent is grounded in those objectives, every question is measurable and every answer is checkable.
>
> **What we built.** VIVA is a full-stack product:
>
> - **Landing** — a judge-facing start screen with demo personas: a struggling IT support specialist, a strong senior data engineer, and a legacy systems engineer who passed every mission. Plus a browser over all 20 cohort candidates with their mission records.
> - **The Interview** — a live, adaptive conversation. The agent starts from your record, picks the next uncovered **completed** day, and adjusts difficulty from your answers. Weak answer? Grounded follow-up naming the exact concept you missed. Stuck? A hint. Vague claim? An overclaim check. The panel on the right shows live progress: question count, phase, and a coverage grid over your completed curriculum days.
> - **The Report** — an Engineering Assessment, not a chatbot summary. Verdict, coverage percentage, strengths, gaps, and next steps — every item linked to a curriculum day and backed by transcript evidence. Copy a shareable link or print it.
>
> **How it works.** A director agent decides the next action: new question, follow-up, or hint. A grader runs retrieval + concept detection against the curriculum — every grade is evidence-grounded, with confidence scores, not vibes. A belief state tracks mastery per day and adapts the rest of the interview. Hints and follow-ups fire on deterministic signals, so the demo never depends on an external LLM — the default runs a deterministic provider that never dies.
>
> **Engineering discipline.** 89 backend tests, 9 frontend tests, deterministic evaluation engine, frozen milestone architecture, and a transcript that carries grounded metadata — follow-up reasons, missing concepts, retrieval confidence — that the UI renders as evidence chips.
>
> **The ask.** Judges, pick any persona. Watch the interview adapt in real time. Then open the report — it's the kind of artifact a hiring manager could actually use.

---

## 3. The 5-Minute Demo Script

**Setup (before judges arrive):**
- Browser open at `http://localhost:8000` (or the deployed URL), production build running.
- Second tab with a completed report already open (`viva-cand-001-…` share link) — the "copy link" reveal.
- Ensure the interviewer tab is on the Landing page.

**Minute 1 — The Hook (Landing)**
- Say: "This is VIVA — an adaptive interview agent for AI engineers."
- Point at the hero, the three demo personas. Say: "These are real cohort members with real mission records — not test fixtures."
- Click **Gerald Combs — IT Support Specialist** (stretch story: 20 years experience, 5/10 missions passed). Say: "He's the struggle story — this is where adaptive interviewing matters."

**Minute 2 — The Interview (Day 1)**
- The interview auto-starts. Welcome message appears.
- Type: `I don't know` for the first question. Say: "Watch what happens when a candidate is stuck."
- The agent gives a grounded hint tied to the day's objective. Say: "The hint is not generic — it comes from the curriculum objective for this exact day."
- Answer again vaguely: `We used something like that at work, I don't remember details.` — the agent fires a follow-up naming the missing concepts.

**Minute 3 — Adaptivity + Commands**
- Type `/hint` — say: "Commands work too: `/hint` and `/end`."
- Answer the next question weakly. Say: "The sidebar is the director's dashboard: question count, phase, and the 8 core days of the plan lighting up as they're covered."
- Say: "Every interviewer message is grounded — the report will show exactly which concept was missed, with evidence."

**Minute 4 — The Report**
- Type `/end`. Wait for the completion, then the report loads automatically.
- Say: "Here is the Engineering Assessment — not a score, an evidence-grounded verdict."
- Walk the three metrics: coverage, verdict, turns. Scroll to Strengths, Gaps, Next steps. Say: "Every gap names the day, the expected objective, and the missing concepts."
- Click **Copy link**, paste into the second tab. Say: "A shareable, judge-verifiable report — no login, no account."
- Click **Print** — show the print layout. Say: "It's designed to be printed."

**Minute 5 — The Contrast (Strong candidate)**
- Say: "Now the same engine, opposite outcome." Click **Sarah Johnson — Senior Data Engineer**.
- Rapid-fire 3 good answers (copy from the scripted answers below). Say: "Notice: no hints, no follow-ups — the director doesn't interrupt a strong candidate."
- End with: "Same engine, different candidate, different interview — that's adaptivity."
- Close: "89 backend tests. Deterministic evaluation. Evidence-grounded. VIVA turns a curriculum into proof."

---

## 4. Judge Walkthrough (minute-by-minute, exact clicks and words)

**0:00–0:30 — Opening**
- Screen: Landing page. Say: "You're about to see a live adaptive interview. No slides — the product is the pitch."

**0:30–1:00 — Pick the underdog**
- Click `Gerald Combs — IT Support Specialist` card.
- Say: "20 years in IT, 5 of 10 missions passed. The interesting candidate."

**1:00–1:30 — Stuck candidate**
- First question appears. Type: `not sure i know this`
- Agent replies with a hint. Say: "Grounded hint — it quotes the curriculum objective."

**1:30–2:30 — Follow-up + sidebar**
- Type: `we tried something similar at work but I forget how it works`
- The follow-up names missing concepts. Say: "Notice it didn't move on — it probed the exact gap."
- Point at the right panel: "Question count, phase rail, coverage grid over your completed days."

**2:30–3:00 — Commands**
- Type: `/hint` then `ok i think it means storing text as numbers` — say: "A real answer. The agent grades it and moves on."
- Type: `/end` — say: "Commands: `/hint`, `/end`. Enter to send, Shift+Enter for a newline."

**3:00–3:30 — The report**
- Report auto-loads. Say: "Engineering Assessment." Point to verdict + coverage.
- Scroll to Gaps. Say: "Each gap: day, objective, missing concepts — from the transcript evidence."

**3:30–4:00 — Share + print**
- Click `Copy link`. Open second tab, paste. Say: "Shareable, no login."
- Click `Print`. Say: "Print-ready."

**4:00–4:45 — The strong contrast**
- Click `Back` → Landing → `Sarah Johnson — Senior Data Engineer`.
- 3 good answers: `I used Sentence Transformers and OpenAI Embeddings to convert text to vectors`, `I built a query router that picks between SQL, vector search, or hybrid retrieval`, `I added monitoring with structured logs and dashboards`.
- Say: "No hints, no probes. The director reads confidence and steps aside."

**4:45–5:00 — Close**
- Say: "89 backend tests, 9 frontend tests, deterministic mock provider that never dies, and every claim in that report is traceable to transcript evidence. VIVA — practice that proves mastery."

**Differentiator line (memorize):**
> "Generic AI interviews test whether you sound confident. VIVA tests whether you covered the curriculum — and shows the evidence."

---

## 5. Expected Judge Questions (60)

### Product & business (1–12)

**Q1. What problem does VIVA solve?**
Best: Learners complete structured curricula but can't prove mastery; generic tools give generic questions and unverifiable feedback. VIVA grounds every question and every report claim in the curriculum.
- Technical: objectives stored per day; retrieval maps answers → concepts.
- Business: upskilling platforms, bootcamps, and hiring pipelines need proof-of-mastery artifacts.
- Engineering: grounded evaluation is testable — that's why we have deterministic tests.
- Tradeoff: curriculum-coupled (per-domain reconfiguration needed for other domains).

**Q2. Who is the user?**
Cohort learners, bootcamp graduates, and self-directed engineers; secondarily mentors/managers who receive report links.

**Q3. How is this different from LeetCode-style mock interviews?**
Those test algorithmic recall. VIVA tests applied engineering knowledge against a defined curriculum, with adaptive difficulty and evidence-grounded reports.

**Q4. Is this an assessment tool or a training tool?**
Both by design: hints and follow-ups train during the interview; the report assesses at the end. The verdict is always secondary to the next-steps plan.

**Q5. What would a paid version look like?**
Per-cohort curriculum onboarding, analytics for mentors, anti-cheat telemetry, and org-level report archives.

**Q6. Why 8 questions / a completed-day pool?**
The interview only ever asks about curriculum days you **completed** (passed missions) — never uncompleted, failed, skipped, or not-started days, which surface as record-based diagnostics in the report instead. The run caps at 8 questions by default (configurable via `VIVA_DEFAULT_QUESTIONS`); fewer completed days means a shorter but still complete run.

**Q7. How do you handle a candidate gaming the system?**
Overclaim detection (claiming coverage the record doesn't support) and vague-answer detection; belief state resists one-off good answers — it's a running per-day estimate.

**Q8. Where does the report go?**
Shareable URL (no login), printable, and re-openable from any device — the judge workflow.

**Q9. Why demo personas instead of real users?**
Hackathon context: real cohort data gives a believable, non-fabricated story. The all-20 browser shows the data is real, not scripted.

**Q10. What's the business model?**
B2B: upskilling platforms embed VIVA as their "interview mode"; B2C freemium with report limits.

**Q11. How long does an interview take?**
~5 minutes for 8 questions; longer if the director probes (by design — weak areas take longer).

**Q12. What happens when the candidate is much stronger than the plan?**
The belief state raises difficulty per day; coverage maxes out and the report reads Strong — same engine, different output.

### AI / technical (13–30)

**Q13. Where does the "AI" actually do work?**
A director agent decides hint/follow-up/next; a grader retrieves concepts and grades answers; an interviewer renders questions. All three are deterministic in mock mode — grounded and testable.

**Q14. How is the grading grounded?**
Token-overlap retrieval against per-day objectives, concept detection, vagueness/overclaim signals, confidence scores — no freeform LLM judgment on the critical path.

**Q15. What role does the LLM play?**
Optional: it can render questions/hints/follow-ups with the same schema the deterministic path uses. Default demo runs mock so it never dies mid-demo.

**Q16. How do you prevent hallucinated report claims?**
Every gap/follow-up carries `followup_reason`, `missing_concepts`, and per-day evidence — the frontend renders evidence chips from metadata, never from free text.

**Q17. What is the belief state?**
Per-day mastery estimate updated with weighted scores + prior mission record; drives difficulty and question selection.

**Q18. How does the director decide hint vs follow-up vs next?**
Deterministic signals: terse answers, overclaims, vagueness → follow-up; "I don't know"/hint request → hint; cap of 2 consecutive probes protects the interview arc.

**Q19. Why not use an LLM for everything?**
Cost, latency, and non-determinism — judges need a demo that behaves identically every run.

**Q20. Is the evaluation deterministic?**
Yes in mock mode — that's what the 89 tests assert (grading, retrieval, decisions, report shape).

**Q21. How is the transcript structured?**
Every interviewer entry carries `meta`: action (question/follow_up/hint), day, followup_reason, missing_concepts, retrieval confidence — the report is derived from this metadata.

**Q22. What happens if the LLM errors mid-interview?**
Graceful fallback to deterministic templates for questions, hints, follow-ups (per-agent try/except).

**Q23. How do you keep sessions isolated?**
Per-session locks, SQLite persistence, session TTL, and 60 req/min rate limiting per IP.

**Q24. How does the coverage grid work?**
8 core days (7, 8, 10, 12, 16, 22, 23, 31) — the frontend derives coverage from transcript days.

**Q25. How is the verdict computed?**
Deterministically in the frontend from coverage % and probe count — no LLM in the verdict.

**Q26. Why SQLite?**
Zero-config persistence for a demo; sessions survive restarts; swap-friendly.

**Q27. How fast is a turn?**
1–6 ms mock mode; LLM mode bounded by provider latency with temperature 0.2–0.3.

**Q28. How do you measure "confidence"?**
Retrieval confidence from token overlap; grading confidence from concept hit rates — both recorded per grade.

**Q29. What's the architecture?**
FastAPI app; director/grader/interviewer agents; grounding retrieval layer; state repository (SQLite); agents layer optional LLM gateway; React SPA served by the same process. See §6.

**Q30. Is there auth?**
No — deliberately. Judges must click without an account. Sessions are unguessable IDs with TTL.

### Engineering (31–44)

**Q31. How many tests and what do they cover?**
89 backend (engine decisions, grading, retrieval, routes, edge-case matrix, rate limiting) + 9 frontend (analysis helpers, verdict).

**Q32. What was the edge-case matrix?**
Contract validation: missing fields, oversized messages, unknown sessions, replay-after-completion (409), first-request-with-message, etc. — each with a pinned behavior + test.

**Q33. How is the frontend served?**
Single FastAPI process: `/assets` static + SPA fallback to `index.html` for non-API routes; `/api/*` 404s properly.

**Q34. What's the deployment story?**
`run.sh`: bootstraps venv, builds frontend if needed, starts uvicorn. Production mode = `npm run build` + uvicorn on the same origin.

**Q35. How do you guarantee no secrets leaked?**
`.env.example` only, `.env` git-ignored, keys never logged, repo audited in Phase 6.

**Q36. Why monorepo layout?**
One repo to judge: `app/` backend, `frontend/` SPA, `tests/`, `scripts/`, `data/`, docs.

**Q37. How did you keep the backend frozen?**
Milestones M1–M4 froze logic; M5–M8 built the experience layer around it — one SPA-serving mount (additive), zero engine changes except an M8 template-string bugfix.

**Q38. What does `VIVA_LLM_PROVIDER` do?**
`mock` (default, deterministic), `openai`, `groq` — switch with env vars; same schema, same behavior.

**Q39. How do you handle 100 concurrent interviews?**
Asyncio + per-session locks + SQLite WAL — fine for demo scale; the interface would scale via a real DB.

**Q40. What happens on server restart mid-interview?**
Session persists in SQLite; the client resumes the transcript and the interview continues from the next turn (verified in Phase 1).

**Q41. Why Tailwind v4 / Vite?**
Fast iteration, tiny CSS, 70 kB gzip JS total; no runtime framework overhead.

**Q42. How is accessibility handled?**
aria-live transcript, role=alert errors, role=status loading, keyboard shortcuts (`/`, Enter, Shift+Enter), reduced-motion support, print styles.

**Q43. How long is the build?**
~0.5 s. Bundle: 232 kB JS (70 kB gzip), 38 kB CSS.

**Q44. What's the release process?**
Milestone commits, all green, PROMPTS.md log appended after every phase — audit-trail as a deliverable.

### Demo & judge-specific (45–52)

**Q45. What if the network dies during the demo?**
Mock provider + same-origin serving: the demo is offline-capable end to end.

**Q46. Why does the weak candidate take longer?**
Hints and follow-ups consume turns — the director spends interview time where the gaps are.

**Q47. Can I re-run the same candidate?**
Yes — new session ID each time, unique and timestamped.

**Q48. What if I refresh mid-interview?**
Session resumes from the transcript (localStorage + server state) — verified.

**Q49. How do I verify the report is honest?**
Every gap names day + objective + missing concepts; the transcript accordion in the report shows the raw conversation.

**Q50. Why is the report printable?**
The print stylesheet produces a clean, judge-friendly artifact.

**Q51. What would you add next?**
Future improvements (deliberately not built): voice input, real LLM guardrails UI, admin analytics, multi-curriculum support, anti-cheat telemetry.

**Q52. What's the single most impressive thing?**
The evidence chain: answer → retrieval → concept detection → follow-up reason → report gap → shareable link. Nothing is asserted that isn't in the transcript.

### Rapid-fire technical detail (53–60)

**Q53. What is `prior_for_day`?** The candidate's mission record for a day — initializes belief state. **Q54. What is the follow-up depth cap?** 2 consecutive probes before the director is forced to move on. **Q55. What is the overclaim cap?** Recorded per session (bounded storage). **Q56. What is `RECENT_SCORES_KEEP`?** 20 — sliding window for trend signals. **Q57. What's the session ID format?** `viva-{candidateId}-{base36 timestamp}`. **Q58. What does 409 mean?** The session already completed — replay is blocked. **Q59. What does the phase rail show?** Warm-up → Core → Scenario → Wrap-up phases from question position. **Q60. How is difficulty chosen?** Belief-state mastery below threshold → easier/next concept; above → harder.

---

## 6. Architecture Explanation

### Simple (for non-technical judges)
VIVA is a conversation with a smart tutor who knows your syllabus. It has three jobs: decide what to ask next, check your answer against the syllabus, and write a report with evidence. Everything is stored so you can refresh, share, or print.

### Intermediate
- **FastAPI backend** (single process, asyncio) with three agents: **Director** (what to do next: ask/probe/hint), **Grader** (retrieval + concept detection against curriculum objectives → evidence bundle), **Interviewer** (renders questions/hints/follow-ups from templates or optional LLM).
- **Grounding layer** maps answers to curriculum days via token-overlap retrieval; every grade carries confidence + missing concepts.
- **Belief state** per day, seeded by the candidate's mission record, updated with weighted scores.
- **SQLite session store** with per-session locks, TTL, and rate limiting.
- **React SPA** (Vite + Tailwind) served by the same FastAPI process; report derived deterministically from transcript metadata.

### Deep technical
- `POST /api/interview` — start with full `CandidateProfile`; turns with `message`. Response = reply + done + feedback. `GET /api/interview/{id}` returns transcript (with per-entry `meta`: action, followup_reason, missing_concepts, day, retrieval_confidence) + report.
- Decision pipeline per turn: normalize → `force_wrap` check (max_turns, 8 questions, `/end`) → grade (if question asked) → `Director.decide` (terse/overclaim/vague → follow_up; hint keywords → hint; honesty bonus + shallow depth → hint; else ask_new) → action execution; consecutive-probe cap = 2.
- Grading: token-overlap retrieval vs per-day objective concepts → detected/missing lists, vagueness/overclaim flags, weighted score, honesty bonus; evidence bundle appended to `state.meta` (bounded: last 12).
- Determinism: mock LLM provider returns schematized content; LLM providers (openai/groq) go through the same gateway with try/except fallback to deterministic templates.
- State: SQLite (aiosqlite), per-session asyncio locks, `VIVA_SESSION_TTL_HOURS` cleanup, per-IP rate limit 60/min.
- SPA: Vite build → `/assets` StaticFiles + catch-all route serving `index.html` except `/api/*` (404); asset path traversal guarded with `resolve().is_relative_to(dist_dir)`.
- Tests: 89 backend (pytest, TestClient) + 9 frontend (vitest) — grading, retrieval, decisions, routes, edge-case matrix, verdict.

---

## 7. Top Differentiators

1. **Curriculum-grounded, not generic.** Every question, hint, and follow-up is anchored to a day + objective. Generic tools ask "tell me about your experience"; VIVA asks about the vector database concepts in Day 8 — and knows the expected answer.
2. **Evidence-grounded evaluation.** The report's gaps are derived from transcript metadata (retrieval confidence, missing concepts), not an LLM's vibes. Judge-verifiable.
3. **Adaptive by design, deterministic by default.** Hints and follow-ups fire on hard signals; the demo behaves identically every run — reliability judges can touch.
4. **Belief-state adaptivity.** Difficulty and coverage decisions come from a running per-day estimate seeded by the real mission record — the interview personalizes within 2 turns.
5. **A shareable, printable artifact.** The report is a product — copy link, open anywhere, print cleanly. Most demos end in a chat box; this ends in a deliverable.
6. **Hackathon-grade engineering discipline.** 89 + 9 tests, edge-case matrix, frozen milestones, no secrets, audit-trail PROMPTS.md — it reads like a startup, not a prototype.
7. **Demo-proof architecture.** Offline-capable mock provider, single-process deploy, session resume across refresh — the judge experience is protected from infrastructure failure.

---

## Future Improvements (deliberately NOT built — M8 rule)
- Voice input / TTS interviewer
- Multi-curriculum onboarding UI (admin)
- Mentor analytics dashboards
- Real LLM guardrails tuning UI (temperature, max tokens per agent)
- Anti-cheat telemetry (response timing patterns)
- Stale-tab 409 recovery UX
- Cloud deployment target (Render/Railway) + CI pipeline
