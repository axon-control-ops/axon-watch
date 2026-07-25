#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "CHILD-PROJECT: real child workspace gate (DashPro)"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/4] Restart control-plane to load workspace bindings"
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

echo "[1/4] Bindings contract"
python3 scripts/verify/check_multi_project_bindings.py
echo

echo "[2/4] Workspace binding unit tests"
python3 -m unittest tests.test_workspace_project_bindings tests.test_parity_d4_multi_project -v
echo

echo "[3/4] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[4/4] Live child-project acceptance"
python3 -m unittest tests.test_child_project_workspace_acceptance -v
echo

echo "CHILD-PROJECT PASS"
