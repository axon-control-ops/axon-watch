#!/usr/bin/env bash
# Install user-level systemd units so Axon-X stays up on this machine
# when you are away (machine must stay powered on).
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
for name in axon-watch control-plane; do
  src="${unit_src}/${name}.service"
  dst="${unit_dst}/${name}.service"
  sed "s|%h/axon-nvme/repos/axon-watch|${repo_root}|g" "${src}" >"${dst}"
  # Keep EnvironmentFile as %h expansion for portability.
  echo "Installed ${dst}"
done

systemctl --user daemon-reload
systemctl --user enable axon-watch.service control-plane.service

port_busy() {
  local port="$1"
  ss -ltn "sport = :${port}" 2>/dev/null | rg -q ":${port}"
}

if [[ "${takeover}" -eq 1 ]]; then
  # Stop known bare uvicorn listeners for these ports, then start units.
  for port in 8788 8787; do
    pids="$(ss -ltnp "sport = :${port}" 2>/dev/null | rg -o 'pid=[0-9]+' | cut -d= -f2 | sort -u || true)"
    for pid in ${pids}; do
      echo "Stopping pid ${pid} on port ${port}"
      kill -TERM "${pid}" 2>/dev/null || true
    done
  done
  sleep 2
  systemctl --user restart axon-watch.service
  systemctl --user restart control-plane.service
  systemctl --user --no-pager --full status axon-watch.service control-plane.service || true
  echo "Takeover complete. Check: curl -sS http://127.0.0.1:8787/api/health"
  exit 0
fi

if port_busy 8787 || port_busy 8788; then
  echo "Ports 8787/8788 already in use — units are enabled for login/boot."
  echo "When ready to hand control to systemd: $0 --takeover"
else
  systemctl --user start axon-watch.service control-plane.service
  systemctl --user --no-pager --full status axon-watch.service control-plane.service || true
fi

echo "User linger should stay yes so services survive logout: loginctl enable-linger \$USER"
echo "Remote access still needs a Cloudflare tunnel token (connectors rail shows it missing today)."
