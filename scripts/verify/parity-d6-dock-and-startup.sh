#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D6: dock behavior + browser startup parity gate"
echo

echo "[1/9] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/9] P-D6 dock + startup integration tests"
python3 -m unittest tests.test_parity_d6_dock_and_startup -v
echo

echo "[3/9] Dock behavior contract checker"
python3 ./scripts/verify/check_dock_behavior_contract.py
echo

echo "[4/9] Browser startup contract checker"
python3 ./scripts/verify/check_browser_startup_contract.py
echo

echo "[5/9] Console-web agent dock behavior tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/agent-dock-behavior.test.ts \
  src/lib/dock-seam-layout.test.ts \
  src/lib/agent-dock-width.test.ts
echo

echo "[6/9] Browser startup docs present"
test -f docs/BROWSER_ONLY_STARTUP_CONTRACT.md
test -f docs/PARITY_D6_DOCK_AND_STARTUP.md
echo "  ok browser startup contract docs"
echo

echo "[7/9] Snapshot partial rows cleared"
python3 - <<'PY'
import json
from pathlib import Path

snapshot = json.loads(Path("config/parity-snapshot.json").read_text())
partial = [row["id"] for row in snapshot["behaviors"] if row["status"] == "partially_verified"]
if partial:
    raise SystemExit(f"expected zero partial rows, got {partial}")
if snapshot["summary"]["partially_verified"] != 0:
    raise SystemExit("summary.partially_verified must be 0")
for parity_id in ("dock_behavior", "desktop_and_browser_startup"):
    row = next(entry for entry in snapshot["behaviors"] if entry["id"] == parity_id)
    if row["status"] != "verified":
        raise SystemExit(f"{parity_id} must be verified")
print("snapshot partial rows cleared; dock + startup verified")
PY
echo

echo "[8/9] Phase D closure complete in order file"
python3 - <<'PY'
import json
from pathlib import Path

order = json.loads(Path("config/parity-closure-order.json").read_text())
phase_d = [entry for entry in order["slices"] if entry.get("phase") == "D"]
if not phase_d or any(entry.get("status") != "done" for entry in phase_d):
    pending = [entry["id"] for entry in phase_d if entry.get("status") != "done"]
    raise SystemExit(f"Phase D incomplete; pending slices: {pending}")
if order.get("next_slice") not in {"complete", "none", ""}:
    raise SystemExit(f"expected next_slice complete, got {order.get('next_slice')!r}")
print("Phase D slices done; next_slice=complete")
PY
echo

echo "[9/9] Full verify gate"
npm run verify
echo

echo "P-D6 PASS"
