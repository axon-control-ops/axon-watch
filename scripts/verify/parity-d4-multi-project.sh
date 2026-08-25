#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D4: multi-project / second bound workspace parity gate"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-D4 multi-project integration tests"
python3 -m unittest tests.test_parity_d4_multi_project -v
echo

echo "[3/8] Multi-project bindings contract checker"
python3 ./scripts/verify/check_multi_project_bindings.py
echo

echo "[4/8] Workspace bindings + handoff regression"
python3 -m unittest \
  tests.test_workspace_project_bindings \
  tests.test_control_plane_workspaces \
  tests.test_control_plane_workspace_handoffs \
  -v
echo

echo "[5/8] TEST-1 / TEST-2 live acceptance (when stack available)"
python3 -m unittest \
  tests.test_test1_workspace_project_connection_acceptance \
  tests.test_test2_workspace_handoff_acceptance \
  -v
echo

echo "[6/8] Default bindings file includes watch + local"
python3 - <<'PY'
import json
from pathlib import Path

bindings = json.loads(Path("config/workspace-project-bindings.json").read_text())
for workspace_id in ("workspace_axon_watch", "workspace_dashpro"):
    if workspace_id not in bindings.get("bindings", {}):
        raise SystemExit(f"missing binding: {workspace_id}")
print("watch + local bindings present")
PY
echo

echo "[7/8] P-D4 slice spec present"
test -f docs/PARITY_D4_MULTI_PROJECT.md
echo "  ok docs/PARITY_D4_MULTI_PROJECT.md"
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "P-D4 PASS"
