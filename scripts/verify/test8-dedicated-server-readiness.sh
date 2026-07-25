#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-8: dedicated-server readiness gate"
echo

if [[ -f "$(service_pid_file "control-plane")" ]]; then
  echo "[0/5] Restart control-plane to load deployment readiness fields"
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

echo "[1/5] Deployment config validation"
python3 ./scripts/ops/validate_deployment_config.py
echo

echo "[2/5] Deployment readiness unit tests"
python3 -m unittest tests.test_deployment_readiness -v
echo

echo "[3/5] Live readiness acceptance"
python3 -m unittest tests.test_test8_dedicated_server_acceptance -v
echo

echo "[4/5] Health endpoint regression"
python3 -m unittest tests.test_service_health_endpoints -v
echo

echo "[5/5] Full verify gate"
npm run verify
echo

echo "TEST-8 PASS"
