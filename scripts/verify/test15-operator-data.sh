#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-15: Operator data surface gate"
echo

if [[ -f "$(service_pid_file "axon-watch")" ]]; then
  echo "[0/5] Restart axon-watch to load data snapshot routes"
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
  echo
fi

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/5] Restart control-plane to load data routes"
  stop_service "control-plane"
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
else
  echo "[0/5] Control-plane not running; live acceptance will skip unless stack is up"
  echo
fi

echo "[1/5] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/5] Operator data unit tests"
PYTHONPATH=services/axon-watch python3 -m unittest tests.test_operator_data_snapshot -v
PYTHONPATH=services/control-plane python3 -m unittest tests.test_control_plane_data -v
echo

echo "[3/5] Live operator data acceptance"
PYTHONPATH=services/control-plane python3 -m unittest tests.test_test15_operator_data_acceptance -v
echo

echo "[4/5] Console-web regression"
npm run verify:console-web
echo

echo "TEST-15 PASS"
