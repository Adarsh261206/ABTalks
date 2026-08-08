# VIVA — Final Release Kit (M8 Phase 8)

## Submission Checklist
- [ ] Repo public: `https://github.com/Adarsh261206/ABTalks`
- [ ] README complete (pitch, architecture, run/test, demo script, LLM checklist)
- [ ] PROMPTS.md verbatim audit trail (20 entries, M0 → M8)
- [ ] PRESENTATION.md (pitches, walkthrough, 60 Q&A, architecture, differentiators)
- [ ] LICENSE (MIT) present
- [ ] `.env.example` complete; no `.env`, no secrets, no keys in history
- [ ] No TODOs / FIXME / console.log / placeholder text / Lorem Ipsum
- [ ] No temp files / pyc / logs tracked
- [ ] Backend: `.venv/bin/python -m pytest` green (89)
- [ ] Frontend: `npm run typecheck`, `npm run test` (9), `npm run build` green
- [ ] Smoke suite: `.venv/bin/python scripts/smoke_test.py` → all passed
- [ ] Working tree clean; all commits pushed

## Deployment Checklist
- [ ] `./run.sh` (or: venv → `pip install -e .` → `cd frontend && npm run build` → `uvicorn app.main:app`)
- [ ] Server reachable at `http://localhost:8000`
- [ ] `/health` → 200
- [ ] `/` serves SPA; deep links (`/report`) serve `index.html`
- [ ] `/api/*` unknown → 404 JSON with request_id
- [ ] `data/` auto-created; sessions survive restart (verified)
- [ ] Real-LLM mode: `cp .env.example .env`, set `VIVA_LLM_PROVIDER` + key, restart, run one interview

## Demo Checklist (see PRESENTATION.md walkthrough)
- [ ] Landing loaded, production build (not `npm run dev`)
- [ ] Scripted answers for Gerald (weak) + Sarah (strong) ready
- [ ] Second tab with a pre-generated report link for the Copy-link reveal
- [ ] `/hint` and `/end` commands practiced
- [ ] Print preview checked once
- [ ] Keyboard: `/` focus, Enter send, Shift+Enter newline
- [ ] 5-minute timer + 3-minute fallback version of the script mentally ready
- [ ] Refresh-mid-interview recovery tested once in the demo browser

## Judge Checklist
- [ ] Lead with the differentiator line: "Generic AI interviews test whether you sound confident. VIVA tests whether you covered the curriculum — and shows the evidence."
- [ ] Show the evidence chain: weak answer → follow-up chip (reason + missing concepts) → report gap citing day + objective
- [ ] Show the strong-candidate contrast (no hints, no probes, Strong verdict)
- [ ] Show Copy link → fresh tab → printable report
- [ ] Mention: 89 backend tests, 9 frontend tests, deterministic mock provider, no secrets, verbatim PROMPTS.md audit trail
- [ ] Have PRESENTATION.md Q&A open for the 60 likely questions

## Risk Checklist
| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| LLM provider fails mid-demo | Low (mock default) | Deterministic fallbacks per agent; demo runs mock |
| 429 rate limit | Very low | Human pace ≈ 10 req/min vs 60/min limit; avoid refresh loops |
| Session TTL expiry mid-interview | Low (2h default) | Demo interviews are < 10 min |
| Stale browser cache | Low | Hard-refresh (Cmd+Shift+R) before demo |
| WiFi loss | Low | Everything is same-origin + offline-capable (mock, local SQLite) |
| Report link opened before interview ends | Low | Page shows clear "No completed interview" empty state |

## Rollback Plan
- All milestones are individual commits on `main`. To roll back any change: `git revert <sha>` (or reset to a known-good tag/commit) and re-run the full test suite.
- Known-good checkpoints: `43382ac` (M5), `77ab92e` (M6), `a490f12` (PROMPTS.md rebuild), `cfdd3a1` (M8 deploy).
- `frontend/dist` is a build artifact (git-ignored) — regenerate with `npm run build`; never hand-edit.

## Emergency Plans

### If the API fails (500s / connection refused)
1. Check `/health` — if refused, restart: `pkill -f "uvicorn app.main:app"; ./run.sh`
2. If startup fails, look at `/tmp/viva-server.log` (or terminal) for the traceback; common causes: missing venv (`./run.sh` bootstraps it), missing `frontend/dist` (rebuild), port in use (`PORT=8001 ./run.sh`).
3. Degraded path: run the backend alone and point the dev server at it (`frontend: npm run dev` proxies `/api` to :8000). The SPA itself never blocks the demo.

### If the LLM fails (real-key mode)
1. The app already falls back to deterministic templates per agent — verify by sending one message and watching for a normal reply.
2. No key at demo time: ensure `.env` is absent or `VIVA_LLM_PROVIDER=mock` → restart. The demo never dies.
3. Do not show API errors to judges; the mock path is the demo path by default.

### If the deployment fails (won't boot on the judging machine)
1. Fallback A — dev mode: `uvicorn app.main:app --reload` + `cd frontend && npm run dev` (Vite proxies `/api`).
2. Fallback B — one-liner: `python3 -m venv .venv && ./.venv/bin/pip install -e . && cd frontend && npm i && npm run build && cd .. && ./.venv/bin/uvicorn app.main:app`
3. Fallback C — static demo: open `PRESENTATION.md` demo script and drive from a pre-recorded screen capture if the environment is truly broken.
4. Last resort: `scripts/smoke_test.py` output + the report screenshots tell the story; judges score the submission, not the live machine.

---
Generated 2026-08-08 during M8 Phase 8. Everything in this kit was verified against the deployed app in Phases 1–7.
