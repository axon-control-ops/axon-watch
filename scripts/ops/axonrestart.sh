#!/usr/bin/env bash
# One-word: axonrestart
# Soft restart of the always-on systemd user units, then health check.
#
# Prefer this for routine refreshes. If control-plane is wedged (even /api/health
# times out), use axonrevive instead — systemd soft-stop can hang on a stuck worker.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Restarting Axon-X user services (watch, control-plane, console, public origin)..."
# Soft restart is safe now: uvicorn --timeout-graceful-shutdown 5 + TimeoutStopSec=12
# prevent speak/SSE from holding :8787 dead for ~90s (Vite ECONNREFUSED spam).
systemctl --user restart \
  axon-watch.service \
  control-plane.service \
  console-web.service \
  axon-public-origin-proxy.service

echo
systemctl --user --no-pager --full is-active \
  axon-watch.service \
  control-plane.service \
  console-web.service \
  axon-public-origin-proxy.service
echo
exec "${repo_root}/scripts/dev/check-health.sh"
