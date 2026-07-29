#!/usr/bin/env bash
# Verify the Vite edit window degrades to HTTP 503 while CP is stopped and
# recovers after CP returns. The trap always restores control-plane.service.
set -euo pipefail

VITE_BASE="${AXON_WATCH_VITE_BASE_URL:-http://127.0.0.1:5173}"
CP_BASE="${AXON_WATCH_CONTROL_PLANE_BASE_URL:-http://127.0.0.1:8787}"
tmp="$(mktemp -d)"

restore() {
  systemctl --user start control-plane.service >/dev/null 2>&1 || true
  rm -rf "${tmp}"
}
trap restore EXIT INT TERM

curl -fsS --max-time 3 "${VITE_BASE}/api/health" >"${tmp}/baseline.json"
curl -fsS --max-time 3 "${CP_BASE}/api/health" >/dev/null

systemctl --user stop control-plane.service
for _ in $(seq 1 25); do
  if ! curl -fsS --max-time 1 "${CP_BASE}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

down_code="$(
  curl -sS --max-time 4 \
    -o "${tmp}/down.json" \
    -w '%{http_code}' \
    "${VITE_BASE}/api/health"
)"
if [[ "${down_code}" != "503" ]]; then
  echo "FAIL: expected Vite proxy 503 while CP was down; got ${down_code}" >&2
  exit 1
fi
if ! rg -q '"detail"\s*:\s*"control-plane unavailable"' "${tmp}/down.json"; then
  echo "FAIL: Vite 503 did not include the controlled CP outage payload" >&2
  exit 1
fi

systemctl --user start control-plane.service
for _ in $(seq 1 50); do
  if curl -fsS --max-time 2 "${CP_BASE}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

curl -fsS --max-time 4 "${CP_BASE}/api/health" >"${tmp}/cp-recovered.json"
curl -fsS --max-time 4 "${VITE_BASE}/api/health" >"${tmp}/vite-recovered.json"
if ! rg -q '"service"\s*:\s*"control-plane"' "${tmp}/vite-recovered.json"; then
  echo "FAIL: Vite proxy did not recover after CP returned" >&2
  exit 1
fi

echo "PASS: Vite returned controlled 503 during CP stop and recovered to 200"
