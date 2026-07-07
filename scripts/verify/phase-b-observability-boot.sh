#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "PHASE-B: observability and boot discipline E2E gate (P-B1 … P-B3)"
echo

echo "[1/9] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/9] P-B1 … P-B3 integration tests"
python3 -m unittest \
  tests.test_parity_b1_shell_boot_verify_wiring \
  tests.test_parity_b2_latency_budgets \
  tests.test_parity_b3_boot_critical_fields \
  tests.test_measure_shell_boot \
  -v
echo

echo "[3/9] Verify harness regression"
python3 -m unittest tests.test_verify_harness -v
echo

echo "[4/9] Runtime summary assembler regression"
python3 -m unittest tests.test_runtime_summary_assembler tests.test_control_plane_runtime_summary -v
echo

echo "[5/9] Phase B slice specs present"
for spec in \
  docs/PARITY_B1_INITIAL_SHELL_BOOT.md \
  docs/PARITY_B2_RUNTIME_LATENCY.md \
  docs/PARITY_B3_BOOT_CRITICAL_FIELDS.md
do
  test -f "${spec}"
  echo "  ok ${spec}"
done
echo

echo "[6/9] Boot-critical allowlist checker"
python3 ./scripts/verify/check_runtime_summary_boot_fields.py
echo

echo "[7/9] Phase B closure complete in order file"
python3 - <<'PY'
import json
from pathlib import Path

order = json.loads(Path("config/parity-closure-order.json").read_text())
phase_b = [entry for entry in order["slices"] if entry.get("phase") == "B"]
if not phase_b or any(entry.get("status") != "done" for entry in phase_b):
    pending = [entry["id"] for entry in phase_b if entry.get("status") != "done"]
    raise SystemExit(f"Phase B incomplete; pending slices: {pending}")
if order.get("next_slice") == "P-C1":
    print("Phase B slices done; next_slice=P-C1")
elif order.get("next_slice") == "complete":
    print("Phase B slices done; parity closure complete")
else:
    raise SystemExit(f"unexpected next_slice after Phase B: {order.get('next_slice')!r}")
PY
echo

echo "[8/9] Phase B parity rows verified in snapshot"
python3 - <<'PY'
import json
from pathlib import Path

snapshot = json.loads(Path("config/parity-snapshot.json").read_text())
for parity_id in ("initial_shell_boot_expectations", "runtime_summary_behavior"):
    row = next(entry for entry in snapshot["behaviors"] if entry["id"] == parity_id)
    if row["status"] != "verified":
        raise SystemExit(f"{parity_id} expected verified, got {row['status']!r}")
verified = sum(1 for row in snapshot["behaviors"] if row["status"] == "verified")
partial = sum(1 for row in snapshot["behaviors"] if row["status"] == "partially_verified")
summary = snapshot["summary"]
if summary["verified_v1"] != verified:
    raise SystemExit(f"summary.verified_v1={summary['verified_v1']} != computed {verified}")
if summary["partially_verified"] != partial:
    raise SystemExit(f"summary.partially_verified={summary['partially_verified']} != computed {partial}")
if partial != 0:
    raise SystemExit(f"expected zero partially_verified rows after Phase B, got {partial}")
print(f"Phase B parity rows verified; snapshot counts ok (verified_v1={verified})")
PY
echo

echo "[9/9] Phase B bundle closure (full verify decoupled — see verify:signal-parity-matrix)"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "PHASE-B PASS"
