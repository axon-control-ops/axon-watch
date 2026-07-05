#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-11: workspace shell commands gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/5] Restart control-plane to load shell command routes"
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

echo "[2/5] Shell command unit tests"
python3 -m unittest tests.test_shell_command tests.test_command_executor tests.test_chat_orchestration -v
echo

echo "[3/5] Command shortcut normalization"
python3 -m unittest tests.test_command_shortcuts -v
echo

echo "[4/5] Live workspace shell command acceptance"
python3 -m unittest tests.test_test11_workspace_shell_commands_acceptance -v
echo

echo "[5/5] Production operator + child-project smoke"
npm run verify:production-operator
./scripts/verify/child-project-workspace.sh
echo

echo "TEST-11 PASS"
