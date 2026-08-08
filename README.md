# VIVA — The Interviewer That Knows What You Built

ABTalks Hackathon entry by Adarsh Sharma (M.H. Saboo Siddik College of Engineering).

**Kickoff:** Fri 7 Aug 2026, 8:00 PM IST · **Deadline:** Sun 9 Aug 2026, 8:00 PM IST

VIVA is an evidence-grounded AI interview practice system for a 31-day enterprise AI
cohort. It reads each candidate's mission record, retrieves the exact curriculum
objectives behind every question, scores what was actually covered, probes missed
concepts with visible reasons, and produces an honest, printable engineering assessment.

No generic praise. No hidden reasoning. The evidence you see — concepts, objectives,
confidence — is structured product metadata generated deterministically.

## What makes it different

| Other AI interviews | VIVA |
| --- | --- |
| Score your vibe | Scores your coverage of retrieved curriculum objectives |
| Random follow-ups | Follow-ups probe the specific concept you missed, with the reason shown |
| Generic feedback | Strengths/gaps/next steps cite concrete cohort days |
| LLM "trust me" | Deterministic grounding layer; LLM is optional, mock-safe fallback always works |

## Architecture

```
┌─────────────┐   POST /api/interview   ┌──────────────────────────┐
│  Frontend   │ ──────────────────────▶ │  FastAPI (app/main.py)   │
│  React 18   │ ◀────────────────────── │  ┌────────────────────┐  │
│  Vite+TW4   │   GET /api/interview/{id}│  │ Agentic engine     │  │
│  (frontend/)│                         │  │  Director → decide │  │
└─────────────┘                         │  │  Grader → evidence  │  │
        │  (served by the same FastAPI  │  │  Interviewer → ask │  │
        │   process when dist/ exists)  │  │  Reporter → report │  │
                                        │  └────────────────────┘  │
                                        │  SqliteSessionStore (TTL)│
                                        │  RateLimiter · Locks     │
                                        └──────────────────────────┘
```

Layers (all in `app/`):
- **Belief state** (`core/belief.py`) — per-day mastery blends prior + live grades with
  confidence growth and difficulty tiers.
- **Grounded retrieval** (`core/retrieval.py`, `core/grounding.py`) — deterministic RAG
  over `curriculum.json`: day-exact retrieval, concept detection, confidence scores.
- **Agents** (`agents/`) — Director picks next action (ask / follow-up / hint),
  Grader scores with evidence, Interviewer renders voice (LLM first, template
  fallbacks), Reporter writes the spec feedback (LLM first, deterministic fallback).
- **Meta, not chain-of-thought** — reasoning metadata is structured product data
  (`state.meta["reasoning"]`), never exposed as hidden LLM thought.

## Running it

### 1. Backend

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn app.main:app --reload          # API at http://localhost:8000
```

### 2. Frontend (development)

```bash
cd frontend
npm install
npm run dev                            # http://localhost:5173, proxies /api to :8000
```

### 3. Frontend (production-style single process)

```bash
cd frontend && npm run build           # creates frontend/dist
cd .. && uvicorn app.main:app          # SPA served from the same process at :8000
```

Or one command (bootstraps venv, builds the frontend if needed, starts the server):

```bash
./run.sh                               # http://localhost:8000
```

## Testing

```bash
.venv/bin/python -m pytest             # backend: 89 tests
cd frontend && npm run typecheck       # TypeScript
cd frontend && npm run test            # vitest (pure logic)
cd frontend && npm run build           # tsc + vite build
```

## Demo script (3 personas)

The landing page offers three personas plus all 20 cohort candidates. Run this
exact sequence for the judging walkthrough:

1. **CAND-010 (stretch / struggling)** — "Interview" → answer briefly, hedge, say
   "I don't remember". **Watch for:** a follow-up that names the exact concept you
   missed (the chip shows *why* VIVA probed), then a hint. End early with
   **End** → **Confirm end?**.
2. **CAND-001 (strong senior)** — answer confidently with tool names from the
   curriculum (e.g. "I chunked the documents and used cosine similarity on
   vector embeddings"). **Watch for:** the coverage grid filling, no grounded
   probes, verdict landing on **Strong**.
3. **CAND-019 (non-technical)** — vague, non-technical answers. **Watch for:**
   the interview staying adaptive instead of collapsing, and the report calling
   out retrieval gaps with concrete days.

Every report is shareable via its URL (**Copy link**) and printable
(**Print** → PDF). Keyboard: **/** focuses the answer box, **Enter** sends,
**Shift+Enter** newline, `/hint` and `/end` work in the chat.

## Real LLM verification checklist (pre-submission)

Out of the box VIVA runs on the deterministic mock provider — reliable for
demos, identical contracts. Verify the real-LLM path at least once before
submission:

1. `cp .env.example .env` and set `VIVA_LLM_PROVIDER=openai`, `VIVA_LLM_MODEL`
   (e.g. `gpt-4o-mini`), `VIVA_OPENAI_API_KEY`.
2. Restart `uvicorn app.main:app`.
3. Run one full 8-question interview (demo script above) and check every box:

   - [ ] Follow-up probes still carry `followup_reason` + `missing_concepts`
   - [ ] Hints arrive on a wrong/stuck answer, not randomly
   - [ ] The report cites concrete cohort days in strengths/gaps/next
   - [ ] Verdict badge matches the metrics (coverage % + probes) — never contradicts
   - [ ] Response shape identical to the mock run (contract is stable)

4. If no key is available at demo time, VIVA falls back to the mock provider —
   the demo never dies.

## AI-Usage Log

Every prompt used to build this project is tracked in [PROMPTS.md](PROMPTS.md),
as required by the ABTalks submission checklist.
