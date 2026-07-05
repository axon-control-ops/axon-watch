#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-C1: KAIRO persona operator copy parity gate"
echo

echo "[1/6] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/6] P-C1 persona settings integration tests"
python3 -m unittest tests.test_parity_c1_persona_settings -v
echo

echo "[3/6] Operator presence policy + settings API regression"
python3 -m unittest tests.test_operator_presence -v
echo

echo "[4/6] Console-web persona settings unit tests"
npm run test -w @axon-watch/console-web -- src/lib/operator-presence-settings.test.ts
echo

echo "[5/6] P-C1 slice spec present"
test -f docs/PARITY_C1_KAIRO_PERSONA.md
echo "  ok docs/PARITY_C1_KAIRO_PERSONA.md"
echo

echo "[6/6] Full verify gate"
npm run verify
echo

echo "P-C1 PASS"
