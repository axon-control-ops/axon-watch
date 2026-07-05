#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-A3: review-ready cross-surface parity gate"
echo

python3 ./scripts/verify/check_parity_closure.py
python3 -m unittest tests.test_parity_a3_review_ready_state -v
npm run test -w @axon-watch/console-web -- src/lib/operator-status-radar-view.test.ts
python3 -m unittest \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_mark_review_ready_transitions_executing_to_review_ready \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_resume_from_review_ready_returns_to_executing \
  tests.test_control_plane_runs.ControlPlaneRunsTests.test_complete_from_review_ready_transitions_to_completed \
  tests.test_command_executor.CommandExecutorTests.test_execute_resume_from_review_resumes_primary_review_ready_run \
  -v
npm run verify

echo "P-A3 PASS"
