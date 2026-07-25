#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-13: CLI runtime fabric gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/4] Restart control-plane to load runtime routes"
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
else
  echo "[0/4] Control-plane not running; live acceptance will skip unless stack is up"
  echo
fi

echo "[1/4] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/4] CLI runtime unit tests"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest \
  tests.test_cli_runtime_catalog \
  tests.test_control_plane_runtime_status \
  tests.test_lane_b_agent \
  tests.test_control_plane_chat \
  tests.test_control_plane_runtime_summary \
  -v
echo

echo "[3/4] Live CLI runtime acceptance"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest tests.test_test13_cli_runtime_acceptance -v
echo

echo "[4/4] Console-web regression"
npm run verify:console-web
echo

echo "TEST-13 PASS"
