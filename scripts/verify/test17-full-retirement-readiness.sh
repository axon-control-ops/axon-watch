#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "TEST-17: Full retirement readiness gate (G6.4)"
echo "NOTE: PASS triggers operator review only — does not auto-retire axon-local."
echo

echo "[1/7] Signal parity matrix (G5)"
npm run verify:signal-parity-matrix
echo

echo "[2/7] Connector parity bundle (G4)"
npm run verify:connector-parity
echo

echo "[3/7] Production operator smoke"
npm run verify:production-operator
echo

echo "[4/7] Headed browser smoke"
npm run verify:headed-browser-smoke
echo

echo "[5/7] Parity snapshot retirement flag still false until operator sign-off"
python3 - <<'PY'
import json
from pathlib import Path

snapshot = json.loads(Path("config/parity-snapshot.json").read_text(encoding="utf-8"))
if snapshot.get("full_axon_local_retirement") is True:
    raise SystemExit(
        "full_axon_local_retirement is true without operator sign-off file — revert or sign off explicitly"
    )
print("  ok full_axon_local_retirement=false (expected pre-sign-off)")
PY
echo

echo "[6/7] G6 dry-run operator entry required"
python3 - <<'PY'
from pathlib import Path

doc = Path("docs/PHASE_G6_RETIREMENT_READINESS.md").read_text(encoding="utf-8")
marker = "## G6.2 — One-week"
section_start = doc.find(marker)
if section_start < 0:
    raise SystemExit("missing G6.2 section in PHASE_G6_RETIREMENT_READINESS.md")

section = doc[section_start:]
checked = section.count("- [x]")
if checked < 1:
    raise SystemExit(
        "G6.2 dry-run has no checked items — complete dry-run and mark checklist before TEST-17"
    )
print(f"  ok G6.2 dry-run has {checked} checked item(s)")
PY
echo

echo "[7/7] Intentional discards operator acknowledgment"
python3 - <<'PY'
from pathlib import Path

doc = Path("docs/PHASE_G5_INTENTIONAL_DISCARDS.md").read_text(encoding="utf-8")
if doc.count("- [x]") + doc.count("[x]") < 1:
    raise SystemExit(
        "PHASE_G5_INTENTIONAL_DISCARDS.md has no operator acknowledgments — sign before TEST-17"
    )
print("  ok at least one intentional discard acknowledged")
PY
echo

echo "TEST-17 PASS — operator review required before setting full_axon_local_retirement"
