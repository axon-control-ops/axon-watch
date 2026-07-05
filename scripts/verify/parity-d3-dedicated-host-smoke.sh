#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D3: dedicated-host smoke parity gate"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-D3 dedicated-host smoke integration tests"
python3 -m unittest tests.test_parity_d3_dedicated_host_smoke -v
echo

echo "[3/8] Dedicated deployment smoke contract checker"
python3 ./scripts/verify/check_dedicated_deployment_smoke.py
echo

echo "[4/8] Deployment readiness regression"
python3 -m unittest tests.test_deployment_readiness -v
echo

echo "[5/8] Dedicated server config validation"
python3 ./scripts/ops/validate_deployment_config.py
echo

echo "[6/8] Readiness endpoint includes public_base_url"
python3 - <<'PY'
from pathlib import Path

text = Path("services/control-plane/app/main.py").read_text(encoding="utf-8")
for needle in ("public_base_url", "_public_base_url"):
    if needle not in text:
        raise SystemExit(f"missing readiness field wiring: {needle}")
print("readiness public_base_url wired")
PY
echo

echo "[7/8] P-D3 slice spec present"
test -f docs/PARITY_D3_DEDICATED_HOST_SMOKE.md
echo "  ok docs/PARITY_D3_DEDICATED_HOST_SMOKE.md"
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "P-D3 PASS"
