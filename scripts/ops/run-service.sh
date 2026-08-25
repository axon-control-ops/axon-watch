#!/usr/bin/env bash
# Start one Axon-X service using deployment.env (systemd-friendly wrapper).
set -euo pipefail

service_name="${1:-}"
if [[ -z "${service_name}" ]]; then
  echo "usage: run-service.sh <axon-watch|control-plane|console-web>" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
env_file="${AXON_WATCH_DEPLOYMENT_ENV:-/etc/axon-watch/deployment.env}"

if [[ -f "${env_file}" ]]; then
  # deployment.env is a process environment contract, not only shell-local
  # configuration. Export values while sourcing so Python services and their
  # worker subprocesses inherit the same DB/token/root paths after a manual
  # restart.
  set -a
  # shellcheck disable=SC1090
  source "${env_file}"
  set +a
elif [[ -f "${repo_root}/config/deployment.env.example" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${repo_root}/config/deployment.env.example"
  set +a
fi

: "${AXON_WATCH_REPO_ROOT:=${repo_root}}"
: "${AXON_WATCH_BIND_HOST:=127.0.0.1}"
: "${AXON_WATCH_CONSOLE_WEB_PORT:=4173}"
: "${AXON_WATCH_CONTROL_PLANE_PORT:=8787}"
: "${AXON_WATCH_WATCH_SERVICE_PORT:=8788}"
: "${AXON_WATCH_STATE_DIR:=${AXON_WATCH_REPO_ROOT}/.local/state}"

# Ensure user-local CLIs (gh, cursor, …) remain visible when systemd starts
# control-plane with a minimal PATH.
export PATH="${HOME}/.local/bin:/usr/local/bin:${PATH}"

# CLI runtimes installed via `npm install -g` under nvm (codex, etc.) carry a
# `#!/usr/bin/env node` shebang. Without the nvm bin dir on PATH, systemd's
# minimal environment resolves that shebang to a system `node` (if any) —
# a different major version than the one the package's optional native
# dependency was resolved against — instead of the nvm-managed node the
# global install actually used. Prepend the highest installed nvm version so
# subprocess dispatch stays on the same node the CLI was installed under.
if [[ -d "${HOME}/.nvm/versions/node" ]]; then
  nvm_node_bin="$(find "${HOME}/.nvm/versions/node" -maxdepth 1 -mindepth 1 -type d 2>/dev/null | sort -V | tail -1)"
  if [[ -n "${nvm_node_bin}" && -x "${nvm_node_bin}/bin/node" ]]; then
    export PATH="${nvm_node_bin}/bin:${PATH}"
  fi
fi

# Gate 2 safety net for always-on: if local_token is required but the token is
# missing, mint one into deployment.env so console proxy + CP stay aligned.
auth_mode="${AXON_WATCH_AUTH_MODE:-placeholder}"
operator_token="${AXON_WATCH_OPERATOR_TOKEN:-}"
if [[ "${auth_mode}" == "local_token" || "${auth_mode}" == "token" || "${auth_mode}" == "required" ]]; then
  if [[ -z "${operator_token}" || "${operator_token}" == "replace-me" ]]; then
    operator_token="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
    export AXON_WATCH_OPERATOR_TOKEN="${operator_token}"
    if [[ -f "${env_file}" ]]; then
      if rg -q '^AXON_WATCH_OPERATOR_TOKEN=' "${env_file}" 2>/dev/null; then
        sed -i "s/^AXON_WATCH_OPERATOR_TOKEN=.*/AXON_WATCH_OPERATOR_TOKEN=${operator_token}/" "${env_file}"
      else
        printf 'AXON_WATCH_OPERATOR_TOKEN=%s\n' "${operator_token}" >>"${env_file}"
      fi
      echo "run-service: generated AXON_WATCH_OPERATOR_TOKEN in ${env_file}" >&2
    fi
  fi
  export AXON_WATCH_AUTH_ALLOW_LOOPBACK="${AXON_WATCH_AUTH_ALLOW_LOOPBACK:-0}"
fi

# Prefer an explicit interpreter, then the repo virtualenv, then PATH python3.
if [[ -z "${AXON_WATCH_PYTHON:-}" ]]; then
  if [[ -x "${AXON_WATCH_REPO_ROOT}/.venv/bin/python3" ]]; then
    AXON_WATCH_PYTHON="${AXON_WATCH_REPO_ROOT}/.venv/bin/python3"
  else
    AXON_WATCH_PYTHON="$(command -v python3)"
  fi
fi

mkdir -p "${AXON_WATCH_STATE_DIR}"

case "${service_name}" in
  axon-watch)
    cd "${AXON_WATCH_REPO_ROOT}/services/axon-watch"
    exec "${AXON_WATCH_PYTHON}" -m uvicorn app.main:app \
      --host "${AXON_WATCH_BIND_HOST}" \
      --port "${AXON_WATCH_WATCH_SERVICE_PORT}" \
      --timeout-graceful-shutdown 5
    ;;
  control-plane)
    cd "${AXON_WATCH_REPO_ROOT}/services/control-plane"
    # Cap graceful drain so speak/SSE clients cannot hold :8787 closed for ~90s
    # during systemctl restart (Vite then spam-logs ECONNREFUSED).
    exec "${AXON_WATCH_PYTHON}" -m uvicorn app.main:app \
      --host "${AXON_WATCH_BIND_HOST}" \
      --port "${AXON_WATCH_CONTROL_PLANE_PORT}" \
      --timeout-graceful-shutdown 5
    ;;
  console-web)
    # Always use vite preview so /api proxies to control-plane (same-origin operator UI).
    # Plain http.server on dist/ breaks health checks and the SPA API client.
    cd "${AXON_WATCH_REPO_ROOT}/apps/console-web"
    if [[ ! -d dist ]]; then
      echo "console-web dist missing; run: npm run build -w @axon-watch/console-web" >&2
      exit 1
    fi
    if [[ "${AXON_WATCH_CONSOLE_STATIC_ONLY:-0}" == "1" ]]; then
      exec "${AXON_WATCH_PYTHON}" -m http.server "${AXON_WATCH_CONSOLE_WEB_PORT}" \
        --bind "${AXON_WATCH_BIND_HOST}" \
        --directory dist
    fi
    exec "${AXON_WATCH_REPO_ROOT}/node_modules/.bin/vite" \
      preview \
      --host "${AXON_WATCH_BIND_HOST}" \
      --port "${AXON_WATCH_CONSOLE_WEB_PORT}" \
      --strictPort
    ;;
  *)
    echo "unknown service: ${service_name}" >&2
    exit 1
    ;;
esac
