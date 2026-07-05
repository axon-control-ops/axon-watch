#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-1: real project/workspace connection gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/5] Restart control-plane to load workspace bindings"
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

echo "[2/5] Workspace project binding unit tests"
python3 -m unittest tests.test_workspace_project_bindings tests.test_control_plane_workspaces -v
echo

echo "[3/5] Workspace root binding integration"
python3 -m unittest tests.test_control_plane_terminal.ControlPlaneTerminalTests.test_resolve_workspace_root_uses_project_binding_when_present -v
echo

echo "[4/5] Live workspace project connection acceptance"
python3 -m unittest tests.test_test1_workspace_project_connection_acceptance -v
echo

echo "[5/5] Full verify gate"
npm run verify
echo

echo "TEST-1 PASS"
