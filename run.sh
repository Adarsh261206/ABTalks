#!/usr/bin/env bash
# VIVA production start: builds the frontend if needed and serves app + SPA
# from a single uvicorn process. Safe to run repeatedly.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/uvicorn ]; then
  echo "[viva] creating virtualenv + installing backend..."
  python3 -m venv .venv
  ./.venv/bin/pip install -q -e .
fi

if [ ! -f frontend/dist/index.html ]; then
  echo "[viva] building frontend..."
  (cd frontend && npm install --no-audit --no-fund >/dev/null && npm run build >/dev/null)
fi

echo "[viva] starting VIVA at http://localhost:8000"
exec ./.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
