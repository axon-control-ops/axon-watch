#!/usr/bin/env bash
# run-5173 — Vite HMR edit window for Axon-X console-web on :5173
#
# Keeps always-on daily driver on :4173. Shares control-plane :8787.
# Usage:
#   ./scripts/ops/run-5173.sh
#   npm run run:5173

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PORT="${AXON_WATCH_CONSOLE_EDIT_PORT:-5173}"
HOST="${AXON_WATCH_CONSOLE_EDIT_HOST:-127.0.0.1}"

if ! curl -fsS --max-time 2 "http://127.0.0.1:8787/api/health" >/dev/null 2>&1; then
  echo "run-5173: control-plane :8787 is not healthy." >&2
  echo "Start always-on backends first:" >&2
  echo "  ./scripts/ops/install-user-always-on.sh" >&2
  echo "  # or: ./scripts/dev/up.sh" >&2
  exit 1
fi

if ss -ltn "( sport = :${PORT} )" 2>/dev/null | grep -q ":${PORT}"; then
  echo "run-5173: port ${PORT} is already in use." >&2
  echo "Open http://${HOST}:${PORT}/ or free the port and retry." >&2
  exit 1
fi

echo "run-5173: starting Vite edit window on http://${HOST}:${PORT}/"
echo "run-5173: daily driver stays on http://127.0.0.1:4173/ (same API :8787)"
exec npm run dev -w @axon-watch/console-web -- --host "$HOST" --port "$PORT" --strictPort
