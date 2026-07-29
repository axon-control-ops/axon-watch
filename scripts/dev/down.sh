#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

usage() {
  cat <<EOF
Usage: ./scripts/dev/down.sh [--systemd|--all] [--force]

Stop Axon-X local services.

  (default)     Stop only .local/pids bootstrap processes (never kills systemd).
  --systemd     Also stop always-on user units: axon-watch, control-plane, console-web.
  --all         Alias for --systemd.
  --force       Same as --systemd (explicit full teardown before a clean up).

Examples:
  ./scripts/dev/down.sh
  ./scripts/dev/down.sh --systemd
  ./scripts/dev/restart.sh   # preferred full bounce
EOF
}

if ! parse_dev_stack_args "$@"; then
  usage
  exit 2
fi

load_env
ensure_runtime_dirs
prune_stale_pid_files

echo "Stopping dev bootstrap (.local/pids)..."
stop_service "console-web"
stop_service "control-plane"
stop_service "axon-watch"
cleanup_port_orphans
rm -f "${stack_manifest}"
echo "Stopped bootstrap processes tracked in .local/pids."

if [[ "${DEV_INCLUDE_SYSTEMD}" == "1" ]]; then
  stop_systemd_stack
  # After systemd stop, reap any leftover listeners we own (not foreign).
  cleanup_port_orphans
fi

print_stack_ownership
echo
if port_in_use "${AXON_WATCH_CONTROL_PLANE_PORT}"; then
  echo "NOTE: :${AXON_WATCH_CONTROL_PLANE_PORT} still listening — likely systemd/external ownership."
  echo "      Use ./scripts/dev/down.sh --systemd  or  systemctl --user stop control-plane.service"
else
  echo "Control plane port :${AXON_WATCH_CONTROL_PLANE_PORT} is free."
fi
