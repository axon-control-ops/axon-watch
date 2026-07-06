#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-20: Agent orchestration parity gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/4] Restart control-plane to load orchestration routes"
  stop_service "control-plane"
  start_service \
    "control-plane" \
    "${repo_root}/services/control-plane" \
    "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_CONTROL_PLANE_PORT}"
  wait_for_http \
    "control-plane" \
    "$(service_ready_url "control-plane")" \
    30 \
    "$(service_pid_file "control-plane")"
  echo
fi

echo "[1/4] Control-plane orchestration tests"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest \
  tests.test_lane_b_agent \
  tests.test_cli_runtime_agents \
  tests.test_cli_runtime_approval_gate \
  tests.test_lane_b_run_dispatch \
  tests.test_cli_runtime_process_registry \
  tests.test_control_plane_runtime_status \
  tests.test_control_plane_chat \
  -v
echo

echo "[2/4] CLI runtime regression"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest \
  tests.test_cli_runtime_catalog \
  tests.test_runtime_vault_integration \
  -v
echo

echo "[3/4] Console-web regression"
npm run verify:console-web
echo

echo "TEST-20 PASS"
