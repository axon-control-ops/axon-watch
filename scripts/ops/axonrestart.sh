#!/usr/bin/env bash
# One-word: axonrestart
# Soft restart of the always-on systemd user units, then health check.
#
# Prefer this for routine refreshes. If control-plane is wedged (even /api/health
# times out), use axonrevive instead — systemd soft-stop can hang on a stuck worker.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

wait_cp_health() {
  local attempt
  for attempt in $(seq 1 30); do
    if curl -fsS --max-time 2 "http://127.0.0.1:8787/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.4
  done
  return 1
}

echo "Restarting Axon-X user services (watch → control-plane → console → proxy)..."
# Soft restart is safe now: uvicorn --timeout-graceful-shutdown 5 + TimeoutStopSec=8
# prevent speak/SSE from holding :8787 dead for ~90s (Vite ECONNREFUSED spam).
# Restart sequentially and wait for CP health so :5173 does not sit in a dead window.
systemctl --user restart axon-watch.service
systemctl --user restart control-plane.service
if ! wait_cp_health; then
  echo "WARN: control-plane :8787 did not become healthy within ~12s" >&2
fi
systemctl --user restart console-web.service
systemctl --user restart axon-public-origin-proxy.service

echo
systemctl --user --no-pager --full is-active \
  axon-watch.service \
  control-plane.service \
  console-web.service \
  axon-public-origin-proxy.service
echo
exec "${repo_root}/scripts/dev/check-health.sh"
