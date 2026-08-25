#!/usr/bin/env bash
# run-5173 — stable Vite source window for Axon-X console-web on :5173
#
# Keeps always-on daily driver on :4173. Shares control-plane :8787.
# HMR is deliberately opt-in so agent/source edits cannot flicker an active UI.
# Usage:
#   ./scripts/ops/run-5173.sh
#   ./scripts/ops/run-5173.sh --hmr
#   npm run run:5173

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PORT="${AXON_WATCH_CONSOLE_EDIT_PORT:-5173}"
HOST="${AXON_WATCH_CONSOLE_EDIT_HOST:-127.0.0.1}"
HMR="${AXON_WATCH_VITE_HMR:-0}"

if [[ "${1:-}" == "--hmr" ]]; then
  HMR=1
  shift
fi
if (($#)); then
  echo "run-5173: unknown argument: $1" >&2
  echo "Usage: $0 [--hmr]" >&2
  exit 2
fi
export AXON_WATCH_VITE_HMR="$HMR"

# Load deployment settings so Vite and the control-plane agree on auth mode.
# Browser mutations use the HttpOnly operator session by default. A trusted
# local developer may explicitly restore legacy proxy injection with
# AXON_WATCH_VITE_INJECT_OPERATOR_TOKEN=1.
env_file="${AXON_WATCH_DEPLOYMENT_ENV:-${HOME}/.config/axon-watch/deployment.env}"
if [[ ! -f "${env_file}" && -f /etc/axon-watch/deployment.env ]]; then
  env_file=/etc/axon-watch/deployment.env
fi
if [[ -f "${env_file}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
  echo "run-5173: loaded operator auth from ${env_file}"
else
  echo "run-5173: warning: no deployment.env found; mutating /api calls may 401" >&2
fi

if ! curl -fsS --max-time 2 "http://127.0.0.1:8787/api/health" >/dev/null 2>&1; then
  echo "run-5173: control-plane :8787 is not healthy — attempting start..." >&2
  if systemctl --user start control-plane.service 2>/dev/null; then
    recovered=0
    for _ in $(seq 1 25); do
      if curl -fsS --max-time 2 "http://127.0.0.1:8787/api/health" >/dev/null 2>&1; then
        recovered=1
        break
      fi
      sleep 0.4
    done
    if [[ "${recovered}" -ne 1 ]]; then
      echo "run-5173: control-plane still unhealthy after start." >&2
      echo "Try: systemctl --user status control-plane.service" >&2
      echo "  or: ./scripts/ops/axonrevive.sh" >&2
      exit 1
    fi
    echo "run-5173: control-plane recovered on :8787"
  else
    echo "run-5173: could not start control-plane.service." >&2
    echo "Start always-on backends first:" >&2
    echo "  ./scripts/ops/install-user-always-on.sh" >&2
    echo "  # or: ./scripts/dev/up.sh" >&2
    exit 1
  fi
fi

if ss -ltn "( sport = :${PORT} )" 2>/dev/null | grep -q ":${PORT}"; then
  echo "run-5173: port ${PORT} is already in use." >&2
  echo "Open http://${HOST}:${PORT}/ or free the port and retry." >&2
  exit 1
fi

echo "run-5173: starting Vite source window on http://${HOST}:${PORT}/"
if [[ "$HMR" == "1" ]]; then
  echo "run-5173: HMR enabled — source edits may reload the page."
else
  echo "run-5173: stability mode — HMR disabled; refresh manually to load source edits."
fi
echo "run-5173: daily driver stays on http://127.0.0.1:4173/ (same API :8787)"
vite_bin="${ROOT}/node_modules/.bin/vite"
if [[ ! -x "$vite_bin" ]]; then
  echo "run-5173: Vite is not installed in ${ROOT}/node_modules." >&2
  echo "Install repo dependencies first: npm install" >&2
  exit 127
fi

cd "${ROOT}/apps/console-web"
exec "$vite_bin" --host "$HOST" --port "$PORT" --strictPort
