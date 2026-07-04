#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env

echo "Console web:"
curl -fsS "$(service_health_url "console-web")" >/dev/null
echo "ok $(service_health_url "console-web")"

echo "Control plane health:"
curl -fsS "$(service_health_url "control-plane")"
echo
echo "Control plane readiness:"
curl -fsS "$(service_ready_url "control-plane")"
echo
echo "Watch health:"
curl -fsS "$(service_health_url "axon-watch")"
echo
echo "Watch readiness:"
curl -fsS "$(service_ready_url "axon-watch")"
echo
echo "Runtime summary:"
curl -fsS "$(service_base_url "control-plane")/api/runtime/summary" >/dev/null
echo "ok $(service_base_url "control-plane")/api/runtime/summary"
echo "Inbox:"
curl -fsS "$(service_base_url "control-plane")/api/inbox" >/dev/null
echo "ok $(service_base_url "control-plane")/api/inbox"
echo "Briefing:"
curl -fsS "$(service_base_url "control-plane")/api/briefing" >/dev/null
echo "ok $(service_base_url "control-plane")/api/briefing"
echo "Runs:"
curl -fsS "$(service_base_url "control-plane")/api/runs" >/dev/null
echo "ok $(service_base_url "control-plane")/api/runs"
echo "Workspaces:"
curl -fsS "$(service_base_url "control-plane")/api/workspaces" >/dev/null
echo "ok $(service_base_url "control-plane")/api/workspaces"
echo "Live events (SSE):"
curl -fsS --max-time 3 -H 'Accept: text/event-stream' "$(service_base_url "control-plane")/api/live/events" | head -n 2 >/dev/null
echo "ok $(service_base_url "control-plane")/api/live/events"
echo
