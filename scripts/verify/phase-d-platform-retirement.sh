#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "PHASE-D: platform and retirement blockers E2E gate (P-D1 … P-D6)"
echo

echo "[1/12] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/12] P-D1 … P-D6 integration tests"
python3 -m unittest \
  tests.test_parity_d1_watch_persistence \
  tests.test_parity_d2_delivery_channel_adapters \
  tests.test_parity_d3_dedicated_host_smoke \
  tests.test_parity_d4_multi_project \
  tests.test_parity_d5_voice_deck \
  tests.test_parity_d6_dock_and_startup \
  -v
echo

echo "[3/12] Phase D contract checkers"
python3 ./scripts/verify/check_dedicated_deployment_smoke.py
python3 ./scripts/verify/check_multi_project_bindings.py
python3 ./scripts/verify/check_delivery_channel_adapters.py
python3 ./scripts/verify/check_dock_behavior_contract.py
python3 ./scripts/verify/check_browser_startup_contract.py
echo

echo "[4/12] Phase D slice specs present"
for spec in \
  docs/PARITY_D1_WATCH_PERSISTENCE.md \
  docs/PARITY_D2_DELIVERY_CHANNEL_ADAPTERS.md \
  docs/PARITY_D3_DEDICATED_HOST_SMOKE.md \
  docs/PARITY_D4_MULTI_PROJECT.md \
  docs/PARITY_D5_VOICE_DECK.md \
  docs/PARITY_D6_DOCK_AND_STARTUP.md
do
  test -f "${spec}"
  echo "  ok ${spec}"
done
echo

echo "[5/12] Voice deck boot wiring"
python3 - <<'PY'
from pathlib import Path

app = Path("apps/console-web/src/App.vue").read_text(encoding="utf-8")
if "useVoiceDeckOnBoot" not in app:
    raise SystemExit("App.vue missing useVoiceDeckOnBoot")
print("voice deck boot wired")
PY
echo

echo "[6/12] Phase D closure complete in order file"
python3 - <<'PY'
import json
from pathlib import Path

order = json.loads(Path("config/parity-closure-order.json").read_text())
phase_d = [entry for entry in order["slices"] if entry.get("phase") == "D"]
if not phase_d or any(entry.get("status") != "done" for entry in phase_d):
    pending = [entry["id"] for entry in phase_d if entry.get("status") != "done"]
    raise SystemExit(f"Phase D incomplete; pending slices: {pending}")
if order.get("next_slice") not in {"complete", "none", ""}:
    raise SystemExit(f"expected next_slice complete, got {order.get('next_slice')!r}")
print("Phase D slices done; next_slice=complete")
PY
echo

echo "[7/12] Snapshot partial rows cleared"
python3 - <<'PY'
import json
from pathlib import Path

snapshot = json.loads(Path("config/parity-snapshot.json").read_text())
partial = [row["id"] for row in snapshot["behaviors"] if row["status"] == "partially_verified"]
if partial:
    raise SystemExit(f"expected zero partial rows, got {partial}")
if snapshot["summary"]["partially_verified"] != 0:
    raise SystemExit("summary.partially_verified must be 0")
if snapshot["summary"]["verified_v1"] != 19:
    raise SystemExit(f"expected verified_v1=19, got {snapshot['summary']['verified_v1']}")
print("Phase D parity complete; partially_verified=0")
PY
echo

echo "[8/12] Dedicated deployment validation"
python3 ./scripts/ops/validate_deployment_config.py
echo

echo "[9/12] Multi-project bindings"
python3 ./scripts/verify/check_multi_project_bindings.py
echo

echo "[10/12] Console-web Phase D UI tests"
npm run test -w @axon-watch/console-web -- \
  src/features/voice-deck/voice-deck.test.ts \
  src/lib/agent-dock-behavior.test.ts \
  src/lib/spoken-alert-delivery.test.ts
echo

echo "[11/12] Deployment readiness regression"
python3 -m unittest tests.test_deployment_readiness tests.test_test8_dedicated_server_acceptance -v
echo

echo "[12/12] Phase D bundle closure (full verify decoupled — see verify:signal-parity-matrix)"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "PHASE-D PASS"
