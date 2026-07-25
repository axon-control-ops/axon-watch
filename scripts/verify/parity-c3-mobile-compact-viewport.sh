#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-C3: mobile operator cockpit compactness parity gate"
echo

echo "[1/7] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/7] P-C3 mobile compact viewport integration tests"
python3 -m unittest tests.test_parity_c3_mobile_compact_viewport -v
echo

echo "[3/7] Operator presence + briefing regression"
python3 -m unittest \
  tests.test_control_plane_operator_presence \
  tests.test_operator_presence \
  tests.test_test7_operator_presence_acceptance \
  -v
echo

echo "[4/7] Console-web viewport compact unit tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/viewport-compact.test.ts \
  src/lib/operator-presence.test.ts
echo

echo "[5/7] P-C3 slice spec present"
test -f docs/PARITY_C3_MOBILE_COMPACT_VIEWPORT.md
echo "  ok docs/PARITY_C3_MOBILE_COMPACT_VIEWPORT.md"
echo

echo "[6/7] Shell store exports viewport compact listener hooks"
python3 - <<'PY'
from pathlib import Path
text = Path("apps/console-web/src/stores/shell.ts").read_text(encoding="utf-8")
for needle in (
    "bindViewportCompactListener",
    "syncViewportCompactFromResize",
    "shouldRequestViewportCompactBriefing",
):
    if needle not in text:
        raise SystemExit(f"missing shell hook: {needle}")
print("shell viewport compact hooks present")
PY
echo

echo "[7/7] Full verify gate"
npm run verify
echo

echo "P-C3 PASS"
