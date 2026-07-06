#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-19: Runtime vault integration gate"
echo

if [[ -f "$(service_pid_file "axon-watch")" ]]; then
  echo "[0/6] Restart axon-watch to load runtime-env routes"
  stop_service "axon-watch"
  start_service \
    "axon-watch" \
    "${repo_root}/services/axon-watch" \
    "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_WATCH_SERVICE_PORT}"
  wait_for_http \
    "axon-watch" \
    "$(service_ready_url "axon-watch")" \
    30 \
    "$(service_pid_file "axon-watch")"
  echo
fi

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/6] Restart control-plane to load vault-fed runtime catalog"
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

echo "[1/6] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/6] Runtime vault integration unit tests"
PYTHONPATH=services/axon-watch:services/control-plane "${python_bin}" -m unittest tests.test_runtime_vault_integration -v
PYTHONPATH=services/control-plane "${python_bin}" -m unittest tests.test_cli_runtime_catalog tests.test_control_plane_runtime_status -v
echo

echo "[3/6] Live runtime status vault posture acceptance"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest tests.test_runtime_vault_acceptance -v
echo

echo "[4/6] CLI runtime regression subset"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest tests.test_lane_b_agent tests.test_control_plane_chat -v
echo

echo "[5/6] Console-web regression"
npm run verify:console-web
echo

echo "TEST-19 PASS"
