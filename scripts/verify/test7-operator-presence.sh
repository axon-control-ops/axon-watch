#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-7: spoken alerts, persona, and mobile presence gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/4] Restart control-plane to load operator_presence projection"
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
fi

echo "[1/4] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/4] Operator presence unit tests"
python3 -m unittest tests.test_operator_presence -v
python3 -m unittest tests.test_control_plane_operator_presence -v
echo

echo "[3/4] Live operator presence acceptance"
python3 -m unittest tests.test_test7_operator_presence_acceptance -v
echo

echo "[4/4] Briefing + verify regression"
python3 -m unittest tests.test_control_plane_operator_briefing -v
npm run verify
echo

echo "TEST-7 PASS"
