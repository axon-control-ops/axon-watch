#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-A2: approval boundaries cross-surface parity gate"
echo

echo "[1/6] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/6] P-A2 cross-surface integration tests"
python3 -m unittest tests.test_parity_a2_approval_boundaries -v
echo

echo "[3/6] Mission control + run-selection projection tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/operator-status-radar-view.test.ts \
  src/stores/shell-run-selection.test.ts
echo

echo "[4/6] Approval boundary regression tests"
python3 -m unittest \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_approve_run_moves_awaiting_approval_to_executing \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_reject_run_moves_awaiting_approval_to_cancelled \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_approve_requires_awaiting_approval_phase \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_resume_from_awaiting_approval_fails \
  tests.test_control_plane_operator_briefing.ControlPlaneOperatorBriefingTests.test_briefing_includes_pending_approval_projection \
  -v
echo

echo "[5/6] Run-state transition integrity"
python3 -m unittest tests.test_run_state_transitions.RunStateTransitionTests.test_capability_flags_for_awaiting_approval -v
echo

echo "[6/6] Full verify gate"
npm run verify
echo

echo "P-A2 PASS"
