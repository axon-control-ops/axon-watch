#!/usr/bin/env bash
# One-word: axonrevive
# Recover a wedged always-on stack (empty shell: Runtime unavailable /
# No workspace selected / Briefing unavailable).
#
# Soft systemctl restart can hang when the control-plane worker is stuck.
# This force-kills control-plane, restarts all three units, then health-checks.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

echo "Reviving Axon-X always-on stack..."
echo "  Force-stopping control-plane (SIGKILL) if needed..."
systemctl --user kill -s SIGKILL control-plane.service 2>/dev/null || true
sleep 1

echo "  Restarting axon-watch + control-plane + console-web..."
systemctl --user restart axon-watch.service control-plane.service console-web.service

# Give uvicorn a moment past "Waiting for application startup".
sleep 2

echo
systemctl --user --no-pager --full is-active axon-watch.service control-plane.service console-web.service
echo
echo "Console: http://127.0.0.1:4173  (hard-refresh after revive)"
echo
exec "${repo_root}/scripts/dev/check-health.sh"
