#!/usr/bin/env bash
set -euo pipefail

# Full bounce for always-on + bootstrap: stop systemd units if present, then up --force.
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

stop_retired_cutover_ports() {
  # The :7734 public-origin proxy and :7735 axon-local rollback runtime are
  # suspended until the operator explicitly restores the soft-cutover path.
  systemctl --user disable --now axon-public-origin-proxy.service 2>/dev/null || true

  local port
  local pids
  for port in 7734 7735; do
    pids="$(
      ss -ltnp "sport = :${port}" 2>/dev/null \
        | rg -o 'pid=[0-9]+' \
        | cut -d= -f2 \
        | sort -u \
        || true
    )"
    for pid in ${pids}; do
      echo "Stopping suspended legacy listener :${port} (pid ${pid})"
      kill -TERM "${pid}" 2>/dev/null || true
    done
  done
}

check_health_after_restart() {
  local attempt
  for attempt in 1 2 3; do
    if "${repo_root}/scripts/dev/check-health.sh"; then
      return 0
    fi
    if [[ "${attempt}" -lt 3 ]]; then
      echo "Health probe ${attempt}/3 caught a cold-start timeout; retrying in 2s..."
      sleep 2
    fi
  done
  return 1
}

echo "=== Axon-X restart ==="
"${repo_root}/scripts/dev/down.sh" --systemd "$@"
stop_retired_cutover_ports
"${repo_root}/scripts/dev/up.sh" --force --no-soft-cutover "$@"
check_health_after_restart
