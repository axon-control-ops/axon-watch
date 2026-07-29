#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env

failures=0
note() { printf '%s\n' "$*"; }
ok() { note "ok  $*"; }
bad() { note "FAIL $*"; failures=$((failures + 1)); }
warn() { note "warn $*"; }

echo "=== Axon-X health ==="
print_stack_ownership
echo

probe_http() {
  local label="$1"
  local url="$2"
  local body_file
  body_file="$(mktemp)"
  local code
  code="$(curl -sS --max-time 8 -o "${body_file}" -w '%{http_code}' "${url}" 2>/dev/null || printf '000')"
  if [[ "${code}" == "200" ]]; then
    ok "${label}  ${url}"
    cat "${body_file}"
    echo
  else
    bad "${label}  ${url}  (http ${code})"
    head -c 240 "${body_file}" 2>/dev/null || true
    echo
  fi
  rm -f "${body_file}"
}

probe_http_silent() {
  local label="$1"
  local url="$2"
  if curl -fsS --max-time 8 -o /dev/null "${url}"; then
    ok "${label}  ${url}"
  else
    bad "${label}  ${url}"
  fi
}

echo "Console web:"
probe_http_silent "console-web" "$(service_health_url "console-web")"

echo "Control plane health:"
probe_http "control-plane health" "$(service_health_url "control-plane")"

echo "Control plane readiness:"
probe_http "control-plane readiness" "$(service_ready_url "control-plane")"

echo "Watch health:"
probe_http "watch health" "$(service_health_url "axon-watch")"

echo "Watch readiness:"
probe_http "watch readiness" "$(service_ready_url "axon-watch")"

echo "Control-plane APIs:"
probe_http_silent "runtime summary" "$(service_base_url "control-plane")/api/runtime/summary"
probe_http_silent "inbox" "$(service_base_url "control-plane")/api/inbox"
probe_http_silent "briefing" "$(service_base_url "control-plane")/api/briefing"
probe_http_silent "runs" "$(service_base_url "control-plane")/api/runs"
probe_http_silent "workspaces" "$(service_base_url "control-plane")/api/workspaces"

echo "Live events (SSE):"
live_events_url="$(service_base_url "control-plane")/api/live/events"
live_events_chunk="$(
  curl -sS --max-time 2 -H 'Accept: text/event-stream' "${live_events_url}" 2>/dev/null | head -c 256
)" || true
if [[ "${live_events_chunk}" == *connected* ]]; then
  ok "${live_events_url}"
else
  warn "${live_events_url}"
fi

echo
echo "Console → control-plane proxy:"
console_proxy_url="$(service_base_url "console-web")/api/health"
if curl -fsS --max-time 5 -o /dev/null "${console_proxy_url}"; then
  ok "preview proxy  ${console_proxy_url}"
else
  bad "preview proxy  ${console_proxy_url}  (IDE will show 'could not reach control plane')"
fi

if port_in_use 5173; then
  vite_proxy_url="http://127.0.0.1:5173/api/health"
  if curl -fsS --max-time 5 -o /dev/null "${vite_proxy_url}"; then
    ok "vite proxy     ${vite_proxy_url}"
  else
    bad "vite proxy     ${vite_proxy_url}  (browser on :5173 cannot reach :8787)"
  fi
else
  note "vite-dev :5173 not listening (optional; always-on console is :${AXON_WATCH_CONSOLE_WEB_PORT})"
fi

echo
if (( failures > 0 )); then
  echo "Health FAILED (${failures} check(s))."
  echo "If the IDE shows 'could not reach :8787' but this script says ok, the failure was transient"
  echo "during a control-plane restart (Vite ECONNREFUSED). Retry send, or run:"
  echo "  ./scripts/dev/restart.sh"
  exit 1
fi

echo "Health OK — control plane :${AXON_WATCH_CONTROL_PLANE_PORT} is up."
echo "Browser tip: prefer http://127.0.0.1:${AXON_WATCH_CONSOLE_WEB_PORT}/ (systemd) or :5173 with working /api proxy."
