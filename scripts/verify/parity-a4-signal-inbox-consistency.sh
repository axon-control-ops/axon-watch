#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-A4: signal/inbox consistency cross-surface parity gate"
echo

python3 ./scripts/verify/check_parity_closure.py
python3 -m unittest tests.test_parity_a4_signal_inbox_consistency -v
python3 -m unittest tests.test_signal_consistency -v
python3 -m unittest tests.test_operator_evidence -v
PYTHONPATH="${repo_root}/services/axon-watch" python3 -m unittest tests.test_email_signal -v
npm run verify

echo "P-A4 PASS"
