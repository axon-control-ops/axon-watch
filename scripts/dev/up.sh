#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [[ -f "${repo_root}/.env" ]]; then
  # shellcheck disable=SC1091
  source "${repo_root}/.env"
else
  # shellcheck disable=SC1091
  source "${repo_root}/.env.example"
fi

: "${AXON_WATCH_CONSOLE_WEB_PORT:=4173}"
: "${AXON_WATCH_CONTROL_PLANE_PORT:=8787}"
: "${AXON_WATCH_WATCH_SERVICE_PORT:=8788}"
: "${AXON_WATCH_STATE_DIR:=./.local/state}"

mkdir -p \
  "${repo_root}/.local/logs" \
  "${repo_root}/.local/pids" \
  "${repo_root}/${AXON_WATCH_STATE_DIR#./}"

if [[ -f "${repo_root}/.local/pids/control-plane.pid" ]] || [[ -f "${repo_root}/.local/pids/axon-watch.pid" ]] || [[ -f "${repo_root}/.local/pids/console-web.pid" ]]; then
  echo "Existing pid files found under .local/pids. Run ./scripts/dev/down.sh first."
  exit 1
fi

if [[ ! -d "${repo_root}/node_modules" ]]; then
  echo "Missing root node_modules. Run npm install at the repo root first."
  exit 1
fi

(
  cd "${repo_root}/services/axon-watch"
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_WATCH_SERVICE_PORT}"
) >"${repo_root}/.local/logs/axon-watch.log" 2>&1 &
echo $! >"${repo_root}/.local/pids/axon-watch.pid"

(
  cd "${repo_root}/services/control-plane"
  python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_CONTROL_PLANE_PORT}"
) >"${repo_root}/.local/logs/control-plane.log" 2>&1 &
echo $! >"${repo_root}/.local/pids/control-plane.pid"

(
  cd "${repo_root}"
  npm run dev -w @axon-watch/console-web -- --host 127.0.0.1 --port "${AXON_WATCH_CONSOLE_WEB_PORT}"
) >"${repo_root}/.local/logs/console-web.log" 2>&1 &
echo $! >"${repo_root}/.local/pids/console-web.pid"

echo "Started bootstrap services:"
echo "  console-web   http://127.0.0.1:${AXON_WATCH_CONSOLE_WEB_PORT}"
echo "  control-plane http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/health"
echo "  axon-watch    http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}/internal/watch/health"
echo
echo "Logs: .local/logs/"
echo "Stop with: ./scripts/dev/down.sh"
