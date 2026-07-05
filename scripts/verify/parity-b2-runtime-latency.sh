#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-B2: runtime and watch summary latency gate"
echo

echo "[1/4] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/4] P-B2 latency budget tests"
python3 -m unittest tests.test_parity_b2_latency_budgets tests.test_verify_harness -v
echo

echo "[3/4] Latency fixtures present"
for fixture in \
  scripts/verify/fixtures/runtime-summary-latency.ci.json \
  scripts/verify/fixtures/watch-summary-latency.ci.json
do
  test -f "${fixture}"
  echo "  ok ${fixture}"
done
echo

echo "[4/4] Full verify gate"
npm run verify
echo

echo "P-B2 PASS"
