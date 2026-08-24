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

  # Export every assignment from the env file so child processes (uvicorn, MCP)
  # inherit optional secrets such as AXON_WATCH_GOOGLE_CSE_*.
  set -a
  if [[ -f "${repo_root}/.env" ]]; then
    # shellcheck disable=SC1091
    source "${repo_root}/.env"
  elif [[ -f "${repo_root}/.env.example" ]]; then
    # shellcheck disable=SC1091
    source "${repo_root}/.env.example"
  fi
  set +a

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

service_health_ready() {
  local name="$1"
  curl -fsS -o /dev/null "$(service_health_url "${name}")" 2>/dev/null
}

bootstrap_stack_healthy() {
  local name
  while IFS= read -r name; do
    service_health_ready "${name}" || return 1
  done < <(service_names)
}

try_reuse_healthy_bootstrap_stack() {
  bootstrap_stack_healthy || return 1

  prune_stale_pid_files
  write_stack_manifest

  echo "Bootstrap services already healthy on configured ports (external/systemd ownership):"
  echo "  console-web   $(service_health_url "console-web")"
  echo "  control-plane $(service_health_url "control-plane")"
  echo "  axon-watch    $(service_health_url "axon-watch")"
  echo
  echo "Health: ./scripts/dev/check-health.sh"
  echo "Logs: .local/logs/ (dev bootstrap) or journalctl --user -u axon-watch.service"
  echo "Stop dev bootstrap with: ./scripts/dev/down.sh"
  echo "Stop always-on units with: systemctl --user stop axon-watch.service control-plane.service console-web.service"
  return 0
}

listener_managed_externally() {
  local pid="$1"
  [[ -n "${pid}" ]] || return 1

  local cgroup_path="/proc/${pid}/cgroup"
  [[ -f "${cgroup_path}" ]] || return 1

  # User/system systemd units (always-on stack) must survive dev down/up cleanup.
  if grep -q '\.service' "${cgroup_path}" 2>/dev/null; then
    return 0
  fi
  return 1
}

assert_port_free() {
  local port="$1"
  local name="$2"

  if port_in_use "${port}"; then
    echo "Configured port ${port} for ${name} is already in use." >&2
    echo "Run ./scripts/dev/down.sh --systemd (or ./scripts/dev/restart.sh) if always-on units own it." >&2
    echo "Plain ./scripts/dev/down.sh only stops .local/pids bootstrap — not systemd." >&2
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

      if listener_managed_externally "${pid}"; then
        continue
      fi

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
  local manifest_dir
  manifest_dir="$(dirname "${stack_manifest}")"
  if [[ ! -d "${manifest_dir}" ]] || [[ ! -w "${manifest_dir}" ]]; then
    echo "WARN: cannot write stack manifest at ${stack_manifest}; continuing without local state file." >&2
    return 0
  fi

  cat >"${stack_manifest}" <<EOF
AXON_WATCH_PUBLIC_BASE_URL=$(service_base_url "console-web")
AXON_WATCH_CONTROL_PLANE_BASE_URL=$(service_base_url "control-plane")
AXON_WATCH_WATCH_SERVICE_BASE_URL=$(service_base_url "axon-watch")
AXON_WATCH_CONSOLE_WEB_PORT=${AXON_WATCH_CONSOLE_WEB_PORT}
AXON_WATCH_CONTROL_PLANE_PORT=${AXON_WATCH_CONTROL_PLANE_PORT}
AXON_WATCH_WATCH_SERVICE_PORT=${AXON_WATCH_WATCH_SERVICE_PORT}
EOF
}

systemd_unit_for_service() {
  case "$1" in
    console-web) printf '%s' "console-web.service" ;;
    control-plane) printf '%s' "control-plane.service" ;;
    axon-watch) printf '%s' "axon-watch.service" ;;
    *)
      echo "Unknown service: $1" >&2
      return 1
      ;;
  esac
}

systemd_user_available() {
  command -v systemctl >/dev/null 2>&1 || return 1
  systemctl --user show-environment >/dev/null 2>&1
}

describe_port_owner() {
  local port="$1"
  local pids
  pids="$(list_listener_pids "${port}" | tr '\n' ' ' | sed 's/[[:space:]]*$//')"
  if [[ -z "${pids}" ]]; then
    printf 'none'
    return 0
  fi

  local pid
  pid="$(printf '%s\n' ${pids} | head -1)"
  local unit="bootstrap/orphan"
  if listener_managed_externally "${pid}"; then
    local cgroup
    cgroup="$(grep -oE '[^/]+\.service' "/proc/${pid}/cgroup" 2>/dev/null | tail -1 || true)"
    unit="${cgroup:-systemd}"
  elif [[ -f "$(service_pid_file "control-plane")" ]] || [[ -f "$(service_pid_file "console-web")" ]]; then
    unit="dev-bootstrap"
  fi
  local cmd
  cmd="$(ps -o comm= -p "${pid}" 2>/dev/null | tr -d ' ' || true)"
  printf 'pid=%s cmd=%s owner=%s' "${pids}" "${cmd:-?}" "${unit}"
}

control_plane_boot_id() {
  curl -fsS --max-time 3 "$(service_health_url "control-plane")" 2>/dev/null \
    | python3 -c 'import json,sys; print(json.load(sys.stdin).get("boot_id",""))' 2>/dev/null \
    || true
}

print_stack_ownership() {
  echo "Port ownership:"
  echo "  console-web   :${AXON_WATCH_CONSOLE_WEB_PORT}  $(describe_port_owner "${AXON_WATCH_CONSOLE_WEB_PORT}")"
  echo "  control-plane :${AXON_WATCH_CONTROL_PLANE_PORT}  $(describe_port_owner "${AXON_WATCH_CONTROL_PLANE_PORT}")"
  echo "  axon-watch    :${AXON_WATCH_WATCH_SERVICE_PORT}  $(describe_port_owner "${AXON_WATCH_WATCH_SERVICE_PORT}")"
  if port_in_use 5173; then
    echo "  vite-dev      :5173  $(describe_port_owner 5173)  (IDE often uses this; /api proxies to :8787)"
  fi
  local boot_id
  boot_id="$(control_plane_boot_id)"
  if [[ -n "${boot_id}" ]]; then
    echo "  control-plane boot_id=${boot_id}"
  fi
}

stop_systemd_stack() {
  systemd_user_available || {
    echo "systemctl --user unavailable; cannot stop always-on units." >&2
    return 1
  }
  local name unit
  # Stop console first, then CP, then watch (reverse of dependency).
  for name in console-web control-plane axon-watch; do
    unit="$(systemd_unit_for_service "${name}")"
    if systemctl --user is-active --quiet "${unit}" 2>/dev/null; then
      echo "Stopping systemd --user ${unit}..."
      systemctl --user stop "${unit}" || true
    fi
  done
}

restart_systemd_stack() {
  systemd_user_available || {
    echo "systemctl --user unavailable; cannot restart always-on units." >&2
    return 1
  }
  local name unit
  # Start watch → control-plane → console-web.
  for name in axon-watch control-plane console-web; do
    unit="$(systemd_unit_for_service "${name}")"
    echo "Restarting systemd --user ${unit}..."
    systemctl --user restart "${unit}"
  done

  local name
  for name in axon-watch control-plane console-web; do
    wait_for_http "${name}" "$(service_ready_url "${name}")" 45
  done
}

parse_dev_stack_args() {
  # Sets: DEV_FORCE_RESTART DEV_INCLUDE_SYSTEMD DEV_SKIP_SOFT_CUTOVER
  DEV_FORCE_RESTART=0
  DEV_INCLUDE_SYSTEMD=0
  DEV_SKIP_SOFT_CUTOVER=0
  local arg
  for arg in "$@"; do
    case "${arg}" in
      --force|--restart|-f)
        DEV_FORCE_RESTART=1
        DEV_INCLUDE_SYSTEMD=1
        ;;
      --systemd|--all)
        DEV_INCLUDE_SYSTEMD=1
        ;;
      --no-soft-cutover)
        DEV_SKIP_SOFT_CUTOVER=1
        AXON_WATCH_SKIP_SOFT_PUBLIC_CUTOVER=1
        export AXON_WATCH_SKIP_SOFT_PUBLIC_CUTOVER
        ;;
      -h|--help)
        return 2
        ;;
      *)
        echo "Unknown argument: ${arg}" >&2
        return 2
        ;;
    esac
  done
  return 0
}
