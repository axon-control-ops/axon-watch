#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "Production operator smoke gate (:4173 primary)"
echo

echo "[1/6] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/6] Production operator contract"
python3 ./scripts/verify/check_production_operator_surface.py
echo

echo "[3/6] TEST-0 live workspace_smoke acceptance"
python3 -m unittest tests.test_test0_workspace_smoke_acceptance -v
echo

echo "[4/6] TEST-1 live workspace bindings + git status"
python3 -m unittest tests.test_test1_workspace_project_connection_acceptance -v
echo

echo "[5/6] F5 operator polish unit smoke"
npm run test -w @axon-watch/console-web -- \
  src/lib/operator-status-radar-view.test.ts \
  src/lib/workbench-terminal-split.test.ts \
  src/lib/workspace-explorer-view.test.ts \
  src/lib/agent-dock-runtime-view.test.ts
echo

echo "[6/6] Console-web production build"
npm run build -w @axon-watch/console-web
echo

echo "PRODUCTION-OPERATOR PASS"
echo
echo "Primary operator surface: http://127.0.0.1:4173"
echo "Open in browser to complete manual UI check (Operator + IDE mode toggle)."
