#!/usr/bin/env bash
# Start backend (port 8000) and frontend (port 5173). Ctrl+C stops both.
# Mock mode with no key: MOCK_MODE=true ./scripts/dev.sh
set -e
cd "$(dirname "$0")/.."
[ -f .venv/bin/activate ] && . .venv/bin/activate
(cd backend && uvicorn main:app --reload --port 8000) &
BACKEND=$!
trap 'kill $BACKEND 2>/dev/null' EXIT
cd frontend && npm run dev
