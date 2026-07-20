#!/usr/bin/env bash
# Install user-level systemd units so Axon-X stays up on this machine
# when you are away (machine must stay powered on).
#
# Starts: axon-watch :8788, control-plane :8787, console-web :4173
# Does NOT start legacy axon-local :7734.
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

if [[ ! -f "${env_dst}" ]]; then
  cat >"${env_dst}" <<EOF
# Local always-on host (machine stays powered; you may be away).
AXON_WATCH_DEPLOYMENT_MODE=bootstrap
AXON_WATCH_REPO_ROOT=${repo_root}
AXON_WATCH_BIND_HOST=127.0.0.1
AXON_WATCH_PUBLIC_BASE_URL=http://127.0.0.1:4173
AXON_WATCH_CONSOLE_WEB_PORT=4173
AXON_WATCH_CONTROL_PLANE_PORT=8787
AXON_WATCH_WATCH_SERVICE_PORT=8788
AXON_WATCH_CONTROL_PLANE_BASE_URL=http://127.0.0.1:8787
AXON_WATCH_WATCH_SERVICE_BASE_URL=http://127.0.0.1:8788
AXON_WATCH_CORS_ORIGINS=http://127.0.0.1:4173,http://127.0.0.1:5173
AXON_WATCH_STATE_DIR=${repo_root}/.local/state
AXON_WATCH_CONTROL_PLANE_DB=${repo_root}/.local/state/control-plane.sqlite3
AXON_WATCH_WATCH_SERVICE_DB=${repo_root}/.local/state/axon-watch.sqlite3
AXON_WATCH_DEPLOYMENT_ENV=${env_dst}
EOF
  echo "Wrote ${env_dst}"
else
  echo "Keeping existing ${env_dst}"
fi

# Rewrite ExecStart paths in installed units to this checkout.
for name in axon-watch control-plane console-web; do
  src="${unit_src}/${name}.service"
  dst="${unit_dst}/${name}.service"
  sed "s|%h/axon-nvme/repos/axon-watch|${repo_root}|g" "${src}" >"${dst}"
  echo "Installed ${dst}"
done

# Keep legacy :7734 off login autostart.
if [[ -x "${repo_root}/scripts/ops/disable-legacy-7734-autostart.sh" ]]; then
  "${repo_root}/scripts/ops/disable-legacy-7734-autostart.sh"
fi
if [[ -x "${repo_root}/scripts/ops/install-bin-wrappers.sh" ]]; then
  "${repo_root}/scripts/ops/install-bin-wrappers.sh"
fi

systemctl --user daemon-reload
systemctl --user enable axon-watch.service control-plane.service console-web.service

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
  systemctl --user --no-pager --full status axon-watch.service control-plane.service console-web.service || true
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
  systemctl --user start axon-watch.service control-plane.service console-web.service
  systemctl --user --no-pager --full status axon-watch.service control-plane.service console-web.service || true
fi

echo "==> Soft public cutover (:7734 -> :4173) + managed tunnel"
if [[ -x "${repo_root}/scripts/ops/soft-public-cutover.sh" ]]; then
  "${repo_root}/scripts/ops/soft-public-cutover.sh" || \
    echo "WARN: soft-public-cutover failed; public hostname may stay degraded." >&2
fi
curl -sS --max-time 10 -X POST \
  "${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}/api/tunnel/start" \
  | python3 -m json.tool 2>/dev/null || \
  echo "WARN: managed tunnel start failed; check /api/tunnel/status." >&2

echo "User linger should stay yes so services survive logout: loginctl enable-linger \$USER"
echo "Operator surface: http://127.0.0.1:4173  (legacy :7734 autostart disabled; soft-rollback on :7735 via soft cutover)"
echo "Hard CF ingress cutover (optional): CF_API_TOKEN=... ./scripts/ops/set-tunnel-ingress-4173.sh"
