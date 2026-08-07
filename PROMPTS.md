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
