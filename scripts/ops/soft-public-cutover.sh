#!/usr/bin/env bash
# Soft public cutover without Cloudflare API:
#   CF ingress stays on :7734 → local reverse-proxy → Axon-X :4173
#   axon-local moves to :7735 for WhatsApp / legacy soft-rollback.
set -euo pipefail

LEGACY_PORT="${AXON_LEGACY_PORT:-7735}"
PUBLIC_PORT="${AXON_PUBLIC_ORIGIN_PORT:-7734}"
AXON_X_ORIGIN="${AXON_X_ORIGIN:-http://127.0.0.1:4173}"
AXON_LOCAL_ROOT="${AXON_LOCAL_ROOT:-/home/edp/axon-nvme/repos/axon-local}"
STATE_DIR="${AXON_WATCH_STATE_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/.local/state}"
PROXY_PIDFILE="${STATE_DIR}/tunnel/public-origin-proxy.pid"
PROXY_LOG="${STATE_DIR}/tunnel/public-origin-proxy.log"
PROXY_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/public-origin-proxy.py"
if ! mkdir -p "${STATE_DIR}/tunnel" 2>/dev/null || [[ ! -w "${STATE_DIR}/tunnel" ]]; then
  STATE_DIR="/tmp/axon-watch-state"
  PROXY_PIDFILE="${STATE_DIR}/tunnel/public-origin-proxy.pid"
  PROXY_LOG="${STATE_DIR}/tunnel/public-origin-proxy.log"
  mkdir -p "${STATE_DIR}/tunnel"
fi

echo "=== Soft public cutover ==="
echo "public :${PUBLIC_PORT} -> ${AXON_X_ORIGIN}"
echo "legacy axon-local -> :${LEGACY_PORT}"

if ! curl -sS --max-time 5 "${AXON_X_ORIGIN}/api/health" | rg -q '"service"\s*:\s*"control-plane"'; then
  echo "ERROR: Axon-X origin not healthy at ${AXON_X_ORIGIN}/api/health"
  exit 1
fi

# Stop whatever is listening on the public origin port (usually axon-local).
# Avoid `pkill -f` patterns that can match this launcher script itself.
if pid="$(ss -ltnp "sport = :${PUBLIC_PORT}" | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1)" && [[ -n "${pid}" ]]; then
  echo "Stopping PID ${pid} on :${PUBLIC_PORT}"
  kill "${pid}" 2>/dev/null || true
  sleep 1
fi

# Ensure legacy axon-local is on the soft-rollback port.
if ! curl -sS --max-time 3 "http://127.0.0.1:${LEGACY_PORT}/api/health" >/dev/null 2>&1; then
  if [[ -d "${AXON_LOCAL_ROOT}" && -x "${AXON_LOCAL_ROOT}/.venv/bin/python" && -f "${AXON_LOCAL_ROOT}/server.py" ]]; then
    echo "Starting axon-local on :${LEGACY_PORT} (WhatsApp soft-rollback)"
    (
      cd "${AXON_LOCAL_ROOT}"
      # Do not start a second cloudflared from axon-local.
      AXON_PORT="${LEGACY_PORT}" AXON_NO_OPEN=1 AXON_START_TUNNEL=0 \
        nohup .venv/bin/python server.py >"/tmp/axon-local-${LEGACY_PORT}.log" 2>&1 &
      disown $! 2>/dev/null || true
    )
    for _ in $(seq 1 30); do
      if curl -sS --max-time 2 "http://127.0.0.1:${LEGACY_PORT}/api/health" >/dev/null 2>&1; then
        break
      fi
      sleep 0.5
    done
  else
    echo "WARN: axon-local checkout not available at ${AXON_LOCAL_ROOT}; skipping legacy soft-rollback start." >&2
  fi
fi

if [[ -f "${PROXY_PIDFILE}" ]]; then
  old="$(cat "${PROXY_PIDFILE}" || true)"
  if [[ -n "${old}" ]] && kill -0 "${old}" 2>/dev/null; then
    echo "Stopping old proxy PID ${old}"
    kill "${old}" 2>/dev/null || true
    sleep 0.5
  fi
fi

if systemctl --user cat axon-public-origin-proxy.service >/dev/null 2>&1; then
  echo "Starting systemd-owned public origin proxy"
  systemctl --user restart axon-public-origin-proxy.service
  proxy_pid="$(systemctl --user show -p MainPID --value axon-public-origin-proxy.service)"
else
  echo "WARN: systemd proxy unit is not installed; using non-durable fallback" >&2
  AXON_X_ORIGIN="${AXON_X_ORIGIN}" AXON_PUBLIC_ORIGIN_PORT="${PUBLIC_PORT}" \
    nohup python3 "${PROXY_SCRIPT}" >"${PROXY_LOG}" 2>&1 &
  proxy_pid=$!
  disown "${proxy_pid}" 2>/dev/null || true
  echo "${proxy_pid}" >"${PROXY_PIDFILE}"
fi
sleep 1

echo "Local public origin:"
curl -sS --max-time 5 "http://127.0.0.1:${PUBLIC_PORT}/api/health" | head -c 200; echo
echo "Legacy soft-rollback:"
curl -sS --max-time 5 "http://127.0.0.1:${LEGACY_PORT}/api/health" | head -c 160; echo
echo "Public hostname:"
curl -sS --max-time 15 "https://axon.edudashpro.org.za/api/health" | head -c 200; echo
echo "DONE soft cutover (proxy pid ${proxy_pid})"
