#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

load_env
ensure_runtime_dirs
prune_stale_pid_files

stop_service "console-web"
stop_service "control-plane"
stop_service "axon-watch"
cleanup_port_orphans
rm -f "${stack_manifest}"

echo "Stopped bootstrap processes tracked in .local/pids."
