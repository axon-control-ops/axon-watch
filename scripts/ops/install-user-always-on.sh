#!/usr/bin/env bash
# Install user-level systemd units so Axon-X stays up on this machine
# when you are away (machine must stay powered on).
#
# Starts: axon-watch :8788, control-plane :8787, console-web :4173
# Does NOT start legacy axon-local or the retired :7734 soft-cutover proxy.
# Cloudflare named tunnel should ingress to :4173 directly.
#
# Usage:
#   ./scripts/ops/install-user-always-on.sh           # install + enable
#   ./scripts/ops/install-user-always-on.sh --takeover  # stop bare listeners, start units
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
unit_src="${repo_root}/infra/systemd/user"
unit_dst="${HOME}/.config/systemd/user"
env_dst="${HOME}/.config/axon-watch/deployment.env"
takeover=0
if [[ "${1:-}" == "--takeover" ]]; then
  takeover=1
fi

mkdir -p "${unit_dst}" "${HOME}/.config/axon-watch"

ensure_gate2_auth_env() {
  local env_file="$1"
  local mode token allow_loop
  mode="$(rg -N '^AXON_WATCH_AUTH_MODE=' "${env_file}" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  token="$(rg -N '^AXON_WATCH_OPERATOR_TOKEN=' "${env_file}" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  allow_loop="$(rg -N '^AXON_WATCH_AUTH_ALLOW_LOOPBACK=' "${env_file}" 2>/dev/null | tail -1 | cut -d= -f2- || true)"

  if [[ -z "${mode}" || "${mode}" == "placeholder" || "${mode}" == "off" ]]; then
    if rg -q '^AXON_WATCH_AUTH_MODE=' "${env_file}" 2>/dev/null; then
      sed -i 's/^AXON_WATCH_AUTH_MODE=.*/AXON_WATCH_AUTH_MODE=local_token/' "${env_file}"
    else
      printf '\n# Gate 2 — mutating API auth (always-on hardened)\nAXON_WATCH_AUTH_MODE=local_token\n' >>"${env_file}"
    fi
  fi

  if [[ -z "${token}" || "${token}" == "replace-me" ]]; then
    token="$(openssl rand -hex 32 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(32))')"
    if rg -q '^AXON_WATCH_OPERATOR_TOKEN=' "${env_file}" 2>/dev/null; then
      sed -i "s/^AXON_WATCH_OPERATOR_TOKEN=.*/AXON_WATCH_OPERATOR_TOKEN=${token}/" "${env_file}"
    else
      printf 'AXON_WATCH_OPERATOR_TOKEN=%s\n' "${token}" >>"${env_file}"
    fi
    echo "Generated AXON_WATCH_OPERATOR_TOKEN in ${env_file}"
  fi

  if [[ -z "${allow_loop}" || "${allow_loop}" == "1" ]]; then
    # Console :4173 proxies as 127.0.0.1; without token injection loopback bypass
    # would let anonymous browser mutations through. Always-on requires the token.
    if rg -q '^AXON_WATCH_AUTH_ALLOW_LOOPBACK=' "${env_file}" 2>/dev/null; then
      sed -i 's/^AXON_WATCH_AUTH_ALLOW_LOOPBACK=.*/AXON_WATCH_AUTH_ALLOW_LOOPBACK=0/' "${env_file}"
    else
      printf 'AXON_WATCH_AUTH_ALLOW_LOOPBACK=0\n' >>"${env_file}"
    fi
  fi
}

ensure_public_origin_env() {
  local env_file="$1"
  local public_origin="https://axon.edudashpro.org.za"
  local cors

  if rg -q '^AXON_WATCH_PUBLIC_BASE_URL=https?://(127\.0\.0\.1|localhost)' "${env_file}"; then
    sed -i "s|^AXON_WATCH_PUBLIC_BASE_URL=.*|AXON_WATCH_PUBLIC_BASE_URL=${public_origin}|" "${env_file}"
  elif ! rg -q '^AXON_WATCH_PUBLIC_BASE_URL=' "${env_file}"; then
    printf 'AXON_WATCH_PUBLIC_BASE_URL=%s\n' "${public_origin}" >>"${env_file}"
  fi

  cors="$(rg -N '^AXON_WATCH_CORS_ORIGINS=' "${env_file}" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if [[ -z "${cors}" ]]; then
    printf 'AXON_WATCH_CORS_ORIGINS=http://127.0.0.1:4173,http://127.0.0.1:5173,%s\n' \
      "${public_origin}" >>"${env_file}"
  elif [[ ",${cors}," != *",${public_origin},"* ]]; then
    sed -i "s|^AXON_WATCH_CORS_ORIGINS=.*|AXON_WATCH_CORS_ORIGINS=${cors},${public_origin}|" "${env_file}"
  fi
}

if [[ ! -f "${env_dst}" ]]; then
  cat >"${env_dst}" <<EOF
# Local always-on host (machine stays powered; you may be away).
AXON_WATCH_DEPLOYMENT_MODE=bootstrap
AXON_WATCH_REPO_ROOT=${repo_root}
AXON_WATCH_BIND_HOST=127.0.0.1
AXON_WATCH_PUBLIC_BASE_URL=https://axon.edudashpro.org.za
AXON_WATCH_CONSOLE_WEB_PORT=4173
AXON_WATCH_CONTROL_PLANE_PORT=8787
AXON_WATCH_WATCH_SERVICE_PORT=8788
AXON_WATCH_CONTROL_PLANE_BASE_URL=http://127.0.0.1:8787
AXON_WATCH_WATCH_SERVICE_BASE_URL=http://127.0.0.1:8788
AXON_WATCH_CORS_ORIGINS=http://127.0.0.1:4173,http://127.0.0.1:5173,https://axon.edudashpro.org.za
AXON_WATCH_STATE_DIR=${repo_root}/.local/state
AXON_WATCH_CONTROL_PLANE_DB=${repo_root}/.local/state/control-plane.sqlite3
AXON_WATCH_WATCH_SERVICE_DB=${repo_root}/.local/state/axon-watch.sqlite3
AXON_WATCH_DEPLOYMENT_ENV=${env_dst}
# Gate 2 — mutating API auth (always-on hardened)
AXON_WATCH_AUTH_MODE=local_token
AXON_WATCH_AUTH_ALLOW_LOOPBACK=0
AXON_WATCH_OPERATOR_TOKEN=
EOF
  echo "Wrote ${env_dst}"
else
  echo "Keeping existing ${env_dst}"
fi
ensure_gate2_auth_env "${env_dst}"
ensure_public_origin_env "${env_dst}"

# Rewrite ExecStart paths in installed units to this checkout.
for name in axon-watch control-plane console-web; do
  src="${unit_src}/${name}.service"
  dst="${unit_dst}/${name}.service"
  sed "s|%h/axon-nvme/repos/axon-watch|${repo_root}|g" "${src}" >"${dst}"
  echo "Installed ${dst}"
done
for name in console-web-rebuild.service console-web-rebuild.path; do
  src="${unit_src}/${name}"
  dst="${unit_dst}/${name}"
  sed "s|%h/axon-nvme/repos/axon-watch|${repo_root}|g" "${src}" >"${dst}"
  echo "Installed ${dst}"
done
# Soft-cutover proxy (:7734 -> :4173) is retired — Cloudflare points at :4173 directly.
systemctl --user disable --now axon-public-origin-proxy.service 2>/dev/null || true

# Keep legacy :7734 off login autostart.
if [[ -x "${repo_root}/scripts/ops/disable-legacy-7734-autostart.sh" ]]; then
  "${repo_root}/scripts/ops/disable-legacy-7734-autostart.sh"
fi
if [[ -x "${repo_root}/scripts/ops/install-bin-wrappers.sh" ]]; then
  "${repo_root}/scripts/ops/install-bin-wrappers.sh"
fi

systemctl --user daemon-reload
systemctl --user enable \
  axon-watch.service \
  control-plane.service \
  console-web.service \
  console-web-rebuild.path

port_busy() {
  local port="$1"
  ss -ltn "sport = :${port}" 2>/dev/null | rg -q ":${port}"
}

if [[ "${takeover}" -eq 1 ]]; then
  # Stop known bare listeners for these ports, then start units.
  for port in 8788 8787 4173; do
    pids="$(ss -ltnp "sport = :${port}" 2>/dev/null | rg -o 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
    for pid in ${pids}; do
      echo "Stopping pid ${pid} on port ${port}"
      kill -TERM "${pid}" 2>/dev/null || true
    done
  done
  sleep 2
  # Ensure console dist exists before starting the unit (avoids vite preview miss).
  if [[ ! -d "${repo_root}/apps/console-web/dist" ]]; then
    echo "Building console-web dist for :4173 ..."
    (cd "${repo_root}" && npm run build -w @axon-watch/console-web)
  fi
  systemctl --user restart axon-watch.service
  systemctl --user restart control-plane.service
  systemctl --user restart console-web.service
  systemctl --user --no-pager --full status \
    axon-watch.service \
    control-plane.service \
    console-web.service || true
  echo "Takeover complete. Check: axonhealth"
  echo "  curl -sS http://127.0.0.1:8787/api/health"
  echo "  curl -sS http://127.0.0.1:4173/api/health"
  exit 0
fi

if port_busy 8787 || port_busy 8788 || port_busy 4173; then
  echo "Ports 4173/8787/8788 already in use — units are enabled for login/boot."
  echo "When ready to hand control to systemd: $0 --takeover"
else
  if [[ ! -d "${repo_root}/apps/console-web/dist" ]]; then
    echo "Building console-web dist for :4173 ..."
    (cd "${repo_root}" && npm run build -w @axon-watch/console-web)
  fi
  systemctl --user start \
    axon-watch.service \
    control-plane.service \
    console-web.service
  systemctl --user --no-pager --full status \
    axon-watch.service \
    control-plane.service \
    console-web.service || true
fi

echo "==> Managed Cloudflare tunnel (ingress should be :4173)"
curl -sS --max-time 10 -X POST \
  "${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}/api/tunnel/start" \
  | python3 -m json.tool 2>/dev/null || \
  echo "WARN: managed tunnel start failed; check /api/tunnel/status." >&2

echo "User linger should stay yes so services survive logout: loginctl enable-linger \$USER"
echo "Operator surface: http://127.0.0.1:4173  (legacy axon-local / :7734 runtime retired; source retained)"
echo "Hard CF ingress cutover (optional): CF_API_TOKEN=... ./scripts/ops/set-tunnel-ingress-4173.sh"
