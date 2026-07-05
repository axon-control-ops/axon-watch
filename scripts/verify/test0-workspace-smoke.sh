#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "TEST-0: workspace_smoke manual acceptance gate"
echo

echo "[1/4] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[2/4] Mission control unit tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/operator-status-radar-view.test.ts \
  src/lib/workbench-terminal-split.test.ts
echo

echo "[3/4] Live workspace_smoke acceptance (control-plane + console-web)"
python3 -m unittest tests.test_test0_workspace_smoke_acceptance -v
echo

echo "[4/4] Full verify gate"
npm run verify
echo

echo "TEST-0 PASS"
