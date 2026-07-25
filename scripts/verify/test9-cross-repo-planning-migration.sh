#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "TEST-9: cross-repo planning migration gate"
echo

echo "[1/4] Planning bundle manifest validation"
python3 ./scripts/ops/planning_bundle_manifest.py validate
echo

echo "[2/4] Planning migration unit tests"
python3 -m unittest tests.test_planning_bundle_migration -v
echo

echo "[3/4] Cutover doc references canonical planning home"
python3 - <<'PY'
from pathlib import Path

repo = Path(".")
cutover = (repo / "docs/AXON_X_CUTOVER_TODO.md").read_text(encoding="utf-8")
if "docs/planning/PARITY_LEDGER.md" not in cutover:
    raise SystemExit("cutover todo must reference docs/planning/PARITY_LEDGER.md")
if "axon-local/Plans/Axon-Watch/PARITY_LEDGER.md" in cutover:
    raise SystemExit("cutover todo must not depend on axon-local planning path")
print("cutover references canonical planning home")
PY
echo

echo "[4/4] Contract verify (scoped — not full verify)"
npm run verify:contracts
echo

echo "TEST-9 PASS"
