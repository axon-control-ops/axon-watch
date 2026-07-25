#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D2: delivery channel adapters parity gate"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-D2 delivery adapter integration tests"
python3 -m unittest tests.test_parity_d2_delivery_channel_adapters -v
echo

echo "[3/8] Delivery adapter + retry unit tests"
python3 -m unittest tests.test_delivery_adapters tests.test_delivery_retry -v
echo

echo "[4/8] Delivery channel contract checker"
python3 ./scripts/verify/check_delivery_channel_adapters.py
echo

echo "[5/8] Delivery receipts regression"
python3 -m unittest \
  tests.test_watch_delivery_receipts \
  tests.test_control_plane_delivery_receipts \
  -v
echo

echo "[6/8] Adapter registry wiring"
python3 - <<'PY'
from pathlib import Path
service = Path("services/axon-watch/app/delivery/service.py").read_text(encoding="utf-8")
if "attempt_channel_delivery" not in service:
    raise SystemExit("delivery service not wired to adapter registry")
print("delivery service uses adapter registry")
PY
echo

echo "[7/8] P-D2 slice spec present"
test -f docs/PARITY_D2_DELIVERY_CHANNEL_ADAPTERS.md
echo "  ok docs/PARITY_D2_DELIVERY_CHANNEL_ADAPTERS.md"
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "P-D2 PASS"
