#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

usage() {
  cat <<EOF
Usage: ./scripts/dev/up.sh [--force|--restart] [--systemd] [--no-public-tunnel]

Start (or reuse) Axon-X console + control-plane + watch.

  (default)          Reuse healthy listeners on :4173/:8787/:8788 (systemd or bootstrap).
  --force|--restart  Bounce always-on systemd units (or start bootstrap if none), wait healthy.
  --systemd          Prefer systemd restart path when units exist.
  --no-public-tunnel Skip managed Cloudflare tunnel start.

Preferred full bounce:
  ./scripts/dev/restart.sh

Health:
  ./scripts/dev/check-health.sh
EOF
}

if ! parse_dev_stack_args "$@"; then
  usage
  exit 2
fi

rollback_stack() {
  stop_service "console-web"
  stop_service "control-plane"
  stop_service "axon-watch"
  cleanup_port_orphans
  rm -f "${stack_manifest}"
}

# Axon-X owns the public path directly. No axon-local soft proxy or legacy
# rollback process is started from this repo.
ensure_managed_tunnel() {
  if [[ "${AXON_WATCH_SKIP_PUBLIC_TUNNEL:-0}" == "1" || "${DEV_SKIP_PUBLIC_TUNNEL}" == "1" ]]; then
    return 0
  fi

  local cp_url="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT:-8787}}"
  echo "Ensuring managed Axon-X tunnel..."
  if ! curl -sS --max-time 10 -X POST "${cp_url}/api/tunnel/start" >/dev/null; then
    echo "WARN: managed tunnel start failed; check connectors rail /api/tunnel/status." >&2
  fi
}

finish_ok() {
  write_stack_manifest
  print_stack_ownership
  echo
  echo "Use console:"
  echo "  always-on  $(service_health_url "console-web")"
  if port_in_use 5173; then
    echo "  vite-dev   http://127.0.0.1:5173/  (proxies /api → :${AXON_WATCH_CONTROL_PLANE_PORT})"
  fi
  echo
  echo "Health: ./scripts/dev/check-health.sh"
  echo "Logs: .local/logs/ (dev bootstrap) or journalctl --user -u control-plane.service"
  echo "Stop bootstrap: ./scripts/dev/down.sh"
  echo "Stop always-on: ./scripts/dev/down.sh --systemd"
}

load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"
ensure_runtime_dirs
require_root_node_modules
prune_stale_pid_files

if [[ "${DEV_FORCE_RESTART}" == "1" ]]; then
  echo "Force restart requested."
  # Tear down bootstrap first so we do not leave duplicate listeners.
  stop_service "console-web"
  stop_service "control-plane"
  stop_service "axon-watch"
  cleanup_port_orphans
  rm -f "${stack_manifest}"

  if systemd_user_available \
    && systemctl --user list-unit-files control-plane.service >/dev/null 2>&1; then
    restart_systemd_stack
    ensure_managed_tunnel
    finish_ok
    exit 0
  fi

  echo "No systemd user units available — starting bootstrap stack."
fi

if [[ "${DEV_FORCE_RESTART}" != "1" ]] && try_reuse_healthy_bootstrap_stack; then
  print_stack_ownership
  ensure_managed_tunnel
  exit 0
fi

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

trap - ERR

ensure_managed_tunnel

echo "Started bootstrap services:"
echo "  console-web   $(service_health_url "console-web")"
echo "  control-plane $(service_health_url "control-plane")"
echo "  axon-watch    $(service_health_url "axon-watch")"
finish_ok
