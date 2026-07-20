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

# Soft public cutover: CF remote ingress stays on :7734, local proxy → Axon-X :4173,
# and the managed Axon-X cloudflared process is started. Do not bind axon-local to :7734.
ensure_soft_public_tunnel() {
  if [[ "${AXON_WATCH_SKIP_SOFT_PUBLIC_CUTOVER:-0}" == "1" ]]; then
    return 0
  fi

  local cp_url="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT:-8787}}"
  echo "Ensuring soft public cutover (:7734 -> :4173) and managed tunnel..."
  if ! "${repo_root}/scripts/ops/soft-public-cutover.sh"; then
    echo "WARN: soft-public-cutover failed; public hostname may stay degraded." >&2
    return 0
  fi
  if ! curl -sS --max-time 10 -X POST "${cp_url}/api/tunnel/start" >/dev/null; then
    echo "WARN: managed tunnel start failed; check connectors rail /api/tunnel/status." >&2
  fi
}

load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"
ensure_runtime_dirs
require_root_node_modules
prune_stale_pid_files

if try_reuse_healthy_bootstrap_stack; then
  ensure_soft_public_tunnel
  exit 0
fi

assert_no_live_pid_files

# Opt-in only: ensuring axon-local on :7734 fights soft public cutover.
if [[ "${AXON_WATCH_ENSURE_LEGACY_7734:-0}" == "1" ]]; then
  axon_local_dir="${AXON_LOCAL_ROOT:-${repo_root}/../axon-local}"
  if [[ -x "${axon_local_dir}/scripts/ops/ensure-server-running.sh" ]]; then
    echo "Ensuring sibling axon-local server on :7734 (AXON_WATCH_ENSURE_LEGACY_7734=1)..."
    if ! "${axon_local_dir}/scripts/ops/ensure-server-running.sh"; then
      echo "WARN: axon-local ensure failed; optional :7734 connector may stay unavailable." >&2
    fi
  fi
fi

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

ensure_soft_public_tunnel

echo "Started bootstrap services:"
echo "  console-web   $(service_health_url "console-web")"
echo "  control-plane $(service_health_url "control-plane")"
echo "  axon-watch    $(service_health_url "axon-watch")"
echo
echo "Health: ./scripts/dev/check-health.sh"
echo "Logs: .local/logs/"
echo "Stop with: ./scripts/dev/down.sh"
