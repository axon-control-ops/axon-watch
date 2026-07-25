#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "TEST-26: Signal parity matrix gate (G5)"
echo

echo "[1/12] Contract tests"
npm run verify:contracts
echo

echo "[2/12] Console-web typecheck + unit + build"
npm run verify:console-web
echo

echo "[3/12] Vault II parity (G1)"
npm run verify:vault-parity
echo

echo "[4/12] Runtime vault integration (G2)"
npm run verify:runtime-vault-integration
echo

echo "[5/12] Agent orchestration parity (G3)"
npm run verify:agent-orchestration-parity
echo

echo "[6/12] Connector parity bundle (G4)"
npm run verify:connector-parity
echo

echo "[7/12] Phase A — run-state trust"
npm run verify:phase-a
echo

echo "[8/12] Phase B — observability boot"
npm run verify:phase-b
echo

echo "[9/12] Phase D — platform retirement slice"
npm run verify:phase-d
echo

echo "[10/12] Production operator smoke"
npm run verify:production-operator
echo

echo "[11/12] Planning bundle manifest"
./scripts/dev/python.sh scripts/ops/planning_bundle_manifest.py validate
echo

echo "[12/12] G5 capability matrix doc"
test -f docs/PHASE_G5_CAPABILITY_MATRIX.md
echo "  ok docs/PHASE_G5_CAPABILITY_MATRIX.md"
echo

echo "TEST-26 PASS"
