#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-2: workspace handoff slice gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/4] Restart control-plane to load handoff routes"
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

echo "[2/4] Workspace handoff unit tests"
python3 -m unittest tests.test_control_plane_workspace_handoffs -v
echo

echo "[3/4] Live workspace handoff acceptance"
python3 -m unittest tests.test_test2_workspace_handoff_acceptance -v
echo

echo "[4/4] Full verify gate"
npm run verify
echo

echo "TEST-2 PASS"
