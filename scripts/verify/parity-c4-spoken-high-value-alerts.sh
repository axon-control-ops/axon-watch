#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-C4: spoken high-value alerts parity gate"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-C4 spoken alert integration tests"
python3 -m unittest tests.test_parity_c4_spoken_high_value_alerts -v
echo

echo "[3/8] Operator presence + spoken policy regression"
python3 -m unittest \
  tests.test_operator_presence \
  tests.test_control_plane_operator_presence \
  tests.test_test7_operator_presence_acceptance \
  -v
echo

echo "[4/8] Spoken alert contract checker"
python3 ./scripts/verify/check_spoken_alert_policy.py
echo

echo "[5/8] Console-web spoken alert delivery tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/spoken-alert-delivery.test.ts \
  src/lib/operator-presence.test.ts
echo

echo "[6/8] Voice-deck hook + settings panel wiring"
python3 - <<'PY'
from pathlib import Path
text = Path("apps/console-web/src/lib/spoken-alert-delivery.ts").read_text(encoding="utf-8")
panel = Path("apps/console-web/src/components/settings/OperatorPresenceSettingsForm.vue").read_text(
    encoding="utf-8"
)
for needle in (
    "registerVoiceDeckSpokenAlertHandler",
    "deliverSpokenOperatorAlert",
    "speakKairoLine",
):
    if needle not in text:
        raise SystemExit(f"missing spoken alert delivery hook: {needle}")
if "spoken_alerts_enabled" not in panel or "Spoken high-value alerts" not in panel:
    raise SystemExit("spoken alerts toggle missing from settings panel")
print("spoken alert delivery + UI toggle present")
PY
echo

echo "[7/8] P-C4 slice spec present"
test -f docs/PARITY_C4_SPOKEN_HIGH_VALUE_ALERTS.md
echo "  ok docs/PARITY_C4_SPOKEN_HIGH_VALUE_ALERTS.md"
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "P-C4 PASS"
