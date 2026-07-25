#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-A1: run stop/resume cross-surface parity gate"
echo

echo "[1/5] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/5] P-A1 cross-surface integration tests"
python3 -m unittest tests.test_parity_a1_run_stop_resume -v
echo

echo "[3/5] Mission control projection tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/operator-status-radar-view.test.ts
echo

echo "[4/5] Run-state regression"
python3 -m unittest tests.test_control_plane_runs.ControlPlaneRunsTests.test_stop_run_pauses_executing_run tests.test_control_plane_runs.ControlPlaneRunsTests.test_resume_run_returns_paused_run_to_executing -v
echo

echo "[5/5] Full verify gate"
npm run verify
echo

echo "P-A1 PASS"
