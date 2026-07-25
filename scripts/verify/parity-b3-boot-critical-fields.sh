#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-B3: runtime summary boot-critical fields gate"
echo

echo "[1/5] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/5] Boot-critical field checker (contract fixture)"
python3 ./scripts/verify/check_runtime_summary_boot_fields.py \
  --payload packages/shared-types/fixtures/runtime-summary.example.json
echo

echo "[3/5] P-B3 boot-critical field tests"
python3 -m unittest tests.test_parity_b3_boot_critical_fields -v
echo

echo "[4/5] Allowlist config present"
test -f config/runtime-summary-boot-critical-fields.json
echo "  ok config/runtime-summary-boot-critical-fields.json"
echo

echo "[5/5] Full verify gate"
npm run verify
echo

echo "P-B3 PASS"
