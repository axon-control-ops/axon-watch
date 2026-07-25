#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-B1: initial shell boot verify wiring gate"
echo

echo "[1/4] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/4] P-B1 shell boot wiring tests"
python3 -m unittest tests.test_parity_b1_shell_boot_verify_wiring -v
echo

echo "[3/4] Shell boot measurement regression"
python3 -m unittest tests.test_measure_shell_boot -v
echo

echo "[4/4] Full verify gate"
npm run verify
echo

echo "P-B1 PASS"
