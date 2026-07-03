#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
pid_dir="${repo_root}/.local/pids"

stop_pid_file() {
  local name="$1"
  local pid_file="${pid_dir}/${name}.pid"

  if [[ ! -f "${pid_file}" ]]; then
    return
  fi

  local pid
  pid="$(<"${pid_file}")"

  if kill -0 "${pid}" 2>/dev/null; then
    kill "${pid}"
  fi

  rm -f "${pid_file}"
}

stop_pid_file "console-web"
stop_pid_file "control-plane"
stop_pid_file "axon-watch"

echo "Stopped bootstrap processes tracked in .local/pids."
