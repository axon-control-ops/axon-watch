#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-5: delivery receipts for operator attention gate"
echo

if [[ -f "$(service_pid_file "axon-watch")" ]]; then
  echo "[0/5] Restart watch + control-plane to load delivery routes"
  stop_service "control-plane"
  stop_service "axon-watch"
  start_service \
    "axon-watch" \
    "${repo_root}/services/axon-watch" \
    python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_WATCH_SERVICE_PORT}"
  wait_for_http \
    "axon-watch" \
    "$(service_ready_url "axon-watch")" \
    30 \
    "$(service_pid_file "axon-watch")"
  start_service \
    "control-plane" \
    "${repo_root}/services/control-plane" \
    python3 -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_CONTROL_PLANE_PORT}"
  wait_for_http \
    "control-plane" \
    "$(service_ready_url "control-plane")" \
    30 \
    "$(service_pid_file "control-plane")"
  echo
fi

echo "[1/5] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/5] Delivery receipt unit tests"
python3 -m unittest tests.test_watch_delivery_receipts -v
python3 -m unittest tests.test_control_plane_delivery_receipts -v
echo

echo "[3/5] Live delivery receipt acceptance"
python3 -m unittest tests.test_test5_delivery_receipts_acceptance -v
echo

echo "[4/5] Watch command + inbox regression"
python3 -m unittest tests.test_watch_commands_events.WatchCommandsAndEventsTests -v
python3 -m unittest tests.test_control_plane_inbox_projection -v
python3 -m unittest tests.test_control_plane_watch_integration -v
echo

echo "[5/5] Full verify gate"
npm run verify
echo

echo "TEST-5 PASS"
