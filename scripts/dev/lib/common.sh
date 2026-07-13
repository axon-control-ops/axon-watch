#!/usr/bin/env bash
# Shared helpers for the Axon-Watch local bootstrap dev scripts.

service_names() {
  printf '%s\n' "console-web" "control-plane" "axon-watch"
}

resolve_repo_root() {
  cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd
}

resolve_python() {
  local root="${1:-${repo_root:-$(resolve_repo_root)}}"
  if [[ -x "${root}/.venv/bin/python3" ]]; then
    printf '%s' "${root}/.venv/bin/python3"
  else
    printf '%s' "python3"
  fi
}

load_env() {
  repo_root="${1:-${repo_root:-$(resolve_repo_root)}}"

  if [[ -f "${repo_root}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${repo_root}/.env"
  elif [[ -f "${repo_root}/.env.example" ]]; then
    # shellcheck disable=SC1091
    source "${repo_root}/.env.example"
  fi

  : "${AXON_WATCH_CONSOLE_WEB_PORT:=4173}"
  : "${AXON_WATCH_CONTROL_PLANE_PORT:=8787}"
  : "${AXON_WATCH_WATCH_SERVICE_PORT:=8788}"
  : "${AXON_WATCH_STATE_DIR:=./.local/state}"
  # Always pin an absolute control-plane DB path so service cwd cannot create/wipe a second store.
  if [[ "${AXON_WATCH_STATE_DIR}" != /* ]]; then
    AXON_WATCH_STATE_DIR="${repo_root}/${AXON_WATCH_STATE_DIR#./}"
  elif [[ "${AXON_WATCH_STATE_DIR}" != "${repo_root}"/* ]]; then
    # Inherited absolute paths (e.g. $HOME/.local/state) silently fork an empty chat DB.
    echo "WARN: AXON_WATCH_STATE_DIR=${AXON_WATCH_STATE_DIR} is outside repo; using ${repo_root}/.local/state" >&2
    AXON_WATCH_STATE_DIR="${repo_root}/.local/state"
  fi
  # Prefer derived DB path under the resolved state dir unless an in-repo absolute override is set.
  if [[ -z "${AXON_WATCH_CONTROL_PLANE_DB:-}" ]] \
    || [[ "${AXON_WATCH_CONTROL_PLANE_DB}" != /* ]] \
    || [[ "${AXON_WATCH_CONTROL_PLANE_DB}" != "${repo_root}"/* ]]; then
    AXON_WATCH_CONTROL_PLANE_DB="${AXON_WATCH_STATE_DIR}/control-plane.sqlite3"
  fi
  : "${AXON_WATCH_PUBLIC_BASE_URL:=http://127.0.0.1:${AXON_WATCH_CONSOLE_WEB_PORT}}"
  : "${AXON_WATCH_CONTROL_PLANE_BASE_URL:=http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}}"
  : "${AXON_WATCH_WATCH_SERVICE_BASE_URL:=http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}}"

  export repo_root
  export AXON_WATCH_CONSOLE_WEB_PORT
  export AXON_WATCH_CONTROL_PLANE_PORT
  export AXON_WATCH_WATCH_SERVICE_PORT
  export AXON_WATCH_STATE_DIR
  export AXON_WATCH_CONTROL_PLANE_DB
  export AXON_WATCH_PUBLIC_BASE_URL
  export AXON_WATCH_CONTROL_PLANE_BASE_URL
  export AXON_WATCH_WATCH_SERVICE_BASE_URL

  stack_manifest="$(manifest_file "${repo_root}")"
  export stack_manifest
}

pids_dir() { printf '%s/.local/pids' "$1"; }
logs_dir() { printf '%s/.local/logs' "$1"; }
manifest_file() { printf '%s/.local/pids/stack.env' "$1"; }

service_pid_file() {
  printf '%s/%s.pid' "$(pids_dir "${repo_root}")" "$1"
}

service_log_file() {
  printf '%s/%s.log' "$(logs_dir "${repo_root}")" "$1"
}

service_port() {
  case "$1" in
    console-web) printf '%s' "${AXON_WATCH_CONSOLE_WEB_PORT}" ;;
    control-plane) printf '%s' "${AXON_WATCH_CONTROL_PLANE_PORT}" ;;
    axon-watch) printf '%s' "${AXON_WATCH_WATCH_SERVICE_PORT}" ;;
    *)
      echo "Unknown service: $1" >&2
      return 1
      ;;
  esac
}

service_base_url() {
  case "$1" in
    console-web) printf '%s' "http://127.0.0.1:${AXON_WATCH_CONSOLE_WEB_PORT}" ;;
    control-plane) printf '%s' "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}" ;;
    axon-watch) printf '%s' "http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}" ;;
    *)
      echo "Unknown service: $1" >&2
      return 1
      ;;
  esac
}

service_health_url() {
  case "$1" in
    console-web) printf '%s/' "$(service_base_url "$1")" ;;
    control-plane) printf '%s/api/health' "$(service_base_url "$1")" ;;
    axon-watch) printf '%s/internal/watch/health' "$(service_base_url "$1")" ;;
    *)
      echo "Unknown service: $1" >&2
      return 1
      ;;
  esac
}

service_ready_url() {
  case "$1" in
    console-web) printf '%s/' "$(service_base_url "$1")" ;;
    control-plane) printf '%s/api/readiness' "$(service_base_url "$1")" ;;
    axon-watch) printf '%s/internal/watch/readiness' "$(service_base_url "$1")" ;;
    *)
      echo "Unknown service: $1" >&2
      return 1
      ;;
  esac
}

ensure_runtime_dirs() {
  mkdir -p \
    "$(logs_dir "${repo_root}")" \
    "$(pids_dir "${repo_root}")" \
    "${repo_root}/${AXON_WATCH_STATE_DIR#./}"
}

require_root_node_modules() {
  if [[ ! -d "${repo_root}/node_modules" ]]; then
    echo "Missing root node_modules. Run npm install at the repo root first." >&2
    return 1
  fi
}

pid_is_alive() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

pid_from_file() {
  local pid_file="$1"
  [[ -f "${pid_file}" ]] || return 1
  tr -d '[:space:]' <"${pid_file}"
}

port_in_use() {
  local port="$1"

  if command -v ss >/dev/null 2>&1; then
    ss -ltn "( sport = :${port} )" 2>/dev/null | awk 'NR > 1 { found = 1 } END { exit(found ? 0 : 1) }'
    return
  fi

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -iTCP:"${port}" -sTCP:LISTEN >/dev/null 2>&1
    return
  fi

  (exec 3<>"/dev/tcp/127.0.0.1/${port}") >/dev/null 2>&1
}

list_listener_pids() {
  local port="$1"

  if command -v lsof >/dev/null 2>&1; then
    lsof -nP -t -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | sort -u
    return
  fi

  if command -v ss >/dev/null 2>&1; then
    ss -ltnp "( sport = :${port} )" 2>/dev/null | awk -F 'pid=' 'NR > 1 && NF > 1 { split($2, a, ","); print a[1] }' | sort -u
  fi
}

assert_port_free() {
  local port="$1"
  local name="$2"

  if port_in_use "${port}"; then
    echo "Configured port ${port} for ${name} is already in use." >&2
    echo "Run ./scripts/dev/down.sh if this is a stale Axon-Watch stack, or free the port before retrying." >&2
    return 1
  fi
}

prune_stale_pid_files() {
  local name
  while IFS= read -r name; do
    local pid_file
    pid_file="$(service_pid_file "${name}")"
    [[ -f "${pid_file}" ]] || continue

    local pid
    pid="$(pid_from_file "${pid_file}" || true)"
    if [[ -z "${pid}" ]] || ! pid_is_alive "${pid}"; then
      rm -f "${pid_file}"
    fi
  done < <(service_names)
}

assert_no_live_pid_files() {
  local conflicts=()
  local name
  while IFS= read -r name; do
    local pid_file
    pid_file="$(service_pid_file "${name}")"
    [[ -f "${pid_file}" ]] || continue

    local pid
    pid="$(pid_from_file "${pid_file}" || true)"
    if [[ -n "${pid}" ]] && pid_is_alive "${pid}"; then
      conflicts+=("${name}:${pid}")
    else
      rm -f "${pid_file}"
    fi
  done < <(service_names)

  if [[ ${#conflicts[@]} -gt 0 ]]; then
    printf 'Existing live bootstrap processes found: %s\n' "${conflicts[*]}" >&2
    echo "Run ./scripts/dev/down.sh first." >&2
    return 1
  fi
}

stop_process_tree() {
  local pid="$1"
  [[ -n "${pid}" ]] || return 0
  pid_is_alive "${pid}" || return 0

  local pgid
  pgid="$(ps -o pgid= -p "${pid}" 2>/dev/null | tr -d ' ')"

  if [[ -n "${pgid}" ]]; then
    kill -TERM "-${pgid}" 2>/dev/null || true
  else
    kill -TERM "${pid}" 2>/dev/null || true
  fi

  local deadline=$((SECONDS + 8))
  while (( SECONDS < deadline )); do
    pid_is_alive "${pid}" || return 0
    sleep 0.3
  done

  if [[ -n "${pgid}" ]]; then
    kill -KILL "-${pgid}" 2>/dev/null || true
  else
    kill -KILL "${pid}" 2>/dev/null || true
  fi
}

stop_service() {
  local name="$1"
  local pid_file
  pid_file="$(service_pid_file "${name}")"
  [[ -f "${pid_file}" ]] || return 0

  local pid
  pid="$(pid_from_file "${pid_file}" || true)"
  if [[ -n "${pid}" ]]; then
    stop_process_tree "${pid}"
  fi
  rm -f "${pid_file}"
}

cleanup_port_orphans() {
  local name
  while IFS= read -r name; do
    local port
    port="$(service_port "${name}")"
    local pid
    while IFS= read -r pid; do
      [[ -n "${pid}" ]] || continue
      pid_is_alive "${pid}" || continue

      local cwd=""
      if [[ -L "/proc/${pid}/cwd" ]]; then
        cwd="$(readlink -f "/proc/${pid}/cwd" 2>/dev/null || true)"
      fi

      local command=""
      command="$(ps -o command= -p "${pid}" 2>/dev/null || true)"

      if [[ "${cwd}" == "${repo_root}"* ]] || [[ "${command}" == *"${repo_root}"* ]]; then
        stop_process_tree "${pid}"
      fi
    done < <(list_listener_pids "${port}")
  done < <(service_names)
}

start_service() {
  local name="$1"
  local cwd="$2"
  shift 2

  local log
  log="$(service_log_file "${name}")"
  local pid_file
  pid_file="$(service_pid_file "${name}")"

  {
    echo "--- start ${name} $(date -u +%Y-%m-%dT%H:%M:%SZ) ---"
  } >>"${log}"

  (
    cd "${cwd}" &&
    exec setsid "$@" >>"${log}" 2>&1
  ) &
  local pid=$!

  echo "${pid}" >"${pid_file}"
}

wait_for_http() {
  local name="$1"
  local url="$2"
  local timeout="${3:-30}"
  local pid_file="${4:-}"
  local deadline=$((SECONDS + timeout))

  while (( SECONDS < deadline )); do
    if curl -fsS -o /dev/null "${url}" 2>/dev/null; then
      return 0
    fi

    if [[ -n "${pid_file}" && -f "${pid_file}" ]]; then
      local pid
      pid="$(pid_from_file "${pid_file}" || true)"
      if [[ -n "${pid}" ]] && ! pid_is_alive "${pid}"; then
        echo "${name} exited before becoming ready. Inspect $(service_log_file "${name}")" >&2
        return 1
      fi
    fi

    sleep 0.5
  done

  echo "${name} did not become ready at ${url} within ${timeout}s. Inspect $(service_log_file "${name}")" >&2
  return 1
}

write_stack_manifest() {
  cat >"${stack_manifest}" <<EOF
AXON_WATCH_PUBLIC_BASE_URL=$(service_base_url "console-web")
AXON_WATCH_CONTROL_PLANE_BASE_URL=$(service_base_url "control-plane")
AXON_WATCH_WATCH_SERVICE_BASE_URL=$(service_base_url "axon-watch")
AXON_WATCH_CONSOLE_WEB_PORT=${AXON_WATCH_CONSOLE_WEB_PORT}
AXON_WATCH_CONTROL_PLANE_PORT=${AXON_WATCH_CONTROL_PLANE_PORT}
AXON_WATCH_WATCH_SERVICE_PORT=${AXON_WATCH_WATCH_SERVICE_PORT}
EOF
}
