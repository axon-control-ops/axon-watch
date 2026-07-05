#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "PHASE-A: run-state trust E2E gate (P-A1 … P-A4)"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-A1 … P-A4 integration tests"
python3 -m unittest \
  tests.test_parity_a1_run_stop_resume \
  tests.test_parity_a2_approval_boundaries \
  tests.test_parity_a3_review_ready_state \
  tests.test_parity_a4_signal_inbox_consistency \
  -v
echo

echo "[3/8] Signal consistency regression"
python3 -m unittest tests.test_signal_consistency -v
echo

echo "[4/8] Console projection tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/operator-status-radar-view.test.ts \
  src/stores/shell-run-selection.test.ts
echo

echo "[5/8] Run-state transition integrity"
python3 -m unittest tests.test_run_state_transitions -v
echo

echo "[6/8] Phase A slice specs present"
for spec in \
  docs/PARITY_A1_RUN_STOP_RESUME.md \
  docs/PARITY_A2_APPROVAL_BOUNDARIES.md \
  docs/PARITY_A3_REVIEW_READY_STATE.md \
  docs/PARITY_A4_SIGNAL_INBOX_CONSISTENCY.md
do
  test -f "${spec}"
  echo "  ok ${spec}"
done
echo

echo "[7/8] Phase A closure complete in order file"
python3 - <<'PY'
import json
from pathlib import Path

order = json.loads(Path("config/parity-closure-order.json").read_text())
phase_a = [entry for entry in order["slices"] if entry.get("phase") == "A"]
if not phase_a or any(entry.get("status") != "done" for entry in phase_a):
    pending = [entry["id"] for entry in phase_a if entry.get("status") != "done"]
    raise SystemExit(f"Phase A incomplete; pending slices: {pending}")
if order.get("next_slice") != "P-B1":
    raise SystemExit(f"expected next_slice P-B1, got {order.get('next_slice')!r}")
print("Phase A slices done; next_slice=P-B1")
PY
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "PHASE-A PASS"
