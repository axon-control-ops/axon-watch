#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env

echo "TEST-16: DashPro / child-project monitor gate"
echo

if [[ -f "$(service_pid_file "axon-watch")" ]]; then
  echo "[0/5] Restart axon-watch to load monitor slice registry"
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

echo "[1/5] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/5] Monitor slice unit tests"
PYTHONPATH=services/axon-watch python3 -m unittest \
  tests.test_monitor_slice_registry \
  tests.test_dashpro_monitor_slice \
  tests.test_dashpro_posthog \
  tests.test_dashpro_sentry \
  tests.test_dashpro_supabase_storage \
  tests.test_dashpro_monitor_vault_action \
  tests.test_actionable_inbox_signals \
  tests.test_operator_briefing_signals \
  -v
echo

echo "[3/5] Live monitor acceptance"
PYTHONPATH=services/axon-watch python3 -m unittest tests.test_test16_dashpro_monitors_acceptance -v
echo

echo "[4/5] Console-web regression"
npm run verify:console-web
echo

echo "TEST-16 PASS"
