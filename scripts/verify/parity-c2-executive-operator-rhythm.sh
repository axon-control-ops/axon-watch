#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-C2: executive operator rhythm parity gate"
echo

echo "[1/7] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/7] P-C2 executive rhythm integration tests"
python3 -m unittest tests.test_parity_c2_executive_operator_rhythm -v
echo

echo "[3/7] Briefing rhythm builder regression"
python3 -m unittest tests.test_operator_briefing_rhythm tests.test_control_plane_operator_briefing -v
echo

echo "[4/7] Executive rhythm contract checker"
python3 ./scripts/verify/check_executive_operator_rhythm.py
echo

echo "[5/7] Console-web briefing + mission projection tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/briefing-panel-view.test.ts \
  src/lib/operator-status-radar-view.test.ts
echo

echo "[6/7] P-C2 slice spec present"
test -f docs/PARITY_C2_EXECUTIVE_OPERATOR_RHYTHM.md
echo "  ok docs/PARITY_C2_EXECUTIVE_OPERATOR_RHYTHM.md"
echo

echo "[7/7] Full verify gate"
npm run verify
echo

echo "P-C2 PASS"
