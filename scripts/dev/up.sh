#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

rollback_stack() {
  stop_service "console-web"
  stop_service "control-plane"
  stop_service "axon-watch"
  cleanup_port_orphans
  rm -f "${stack_manifest}"
}

load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"
ensure_runtime_dirs
require_root_node_modules
prune_stale_pid_files
assert_no_live_pid_files

assert_port_free "${AXON_WATCH_CONSOLE_WEB_PORT}" "console-web"
assert_port_free "${AXON_WATCH_CONTROL_PLANE_PORT}" "control-plane"
assert_port_free "${AXON_WATCH_WATCH_SERVICE_PORT}" "axon-watch"

trap 'rollback_stack' ERR

start_service \
  "axon-watch" \
  "${repo_root}/services/axon-watch" \
  "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_WATCH_SERVICE_PORT}"
wait_for_http \
  "axon-watch" \
  "$(service_ready_url "axon-watch")" \
  30 \
  "$(service_pid_file "axon-watch")"

start_service \
  "control-plane" \
  "${repo_root}/services/control-plane" \
  "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_CONTROL_PLANE_PORT}"
wait_for_http \
  "control-plane" \
  "$(service_ready_url "control-plane")" \
  30 \
  "$(service_pid_file "control-plane")"

start_service \
  "console-web" \
  "${repo_root}/apps/console-web" \
  "${repo_root}/node_modules/.bin/vite" \
  --host 127.0.0.1 \
  --port "${AXON_WATCH_CONSOLE_WEB_PORT}" \
  --strictPort
wait_for_http \
  "console-web" \
  "$(service_ready_url "console-web")" \
  30 \
  "$(service_pid_file "console-web")"

write_stack_manifest
trap - ERR

echo "Started bootstrap services:"
echo "  console-web   $(service_health_url "console-web")"
echo "  control-plane $(service_health_url "control-plane")"
echo "  axon-watch    $(service_health_url "axon-watch")"
echo
echo "Health: ./scripts/dev/check-health.sh"
echo "Logs: .local/logs/"
echo "Stop with: ./scripts/dev/down.sh"
