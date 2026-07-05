#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

echo "P-D5: Vue voice deck parity gate"
echo

echo "[1/8] Parity closure order validation"
python3 ./scripts/verify/check_parity_closure.py
echo

echo "[2/8] P-D5 voice deck integration tests"
python3 -m unittest tests.test_parity_d5_voice_deck -v
echo

echo "[3/8] Console-web voice deck unit tests"
npm run test -w @axon-watch/console-web -- \
  src/features/voice-deck/voice-deck.test.ts \
  src/lib/spoken-alert-delivery.test.ts
echo

echo "[4/8] Spoken alert contract checker"
python3 ./scripts/verify/check_spoken_alert_policy.py
echo

echo "[5/8] Voice deck boot wiring"
python3 - <<'PY'
from pathlib import Path

app = Path("apps/console-web/src/App.vue").read_text(encoding="utf-8")
deck = Path("apps/console-web/src/features/voice-deck/voice-deck.ts").read_text(encoding="utf-8")
for needle in ("useVoiceDeckOnBoot", "registerVoiceDeckSpokenAlertHandler", "handleVoiceDeckSpokenAlert"):
    if needle not in app and needle not in deck:
        raise SystemExit(f"missing voice deck wiring: {needle}")
print("voice deck boot wiring present")
PY
echo

echo "[6/8] Operator presence regression"
python3 -m unittest tests.test_operator_presence tests.test_control_plane_operator_presence -v
echo

echo "[7/8] P-D5 slice spec present"
test -f docs/PARITY_D5_VOICE_DECK.md
echo "  ok docs/PARITY_D5_VOICE_DECK.md"
echo

echo "[8/8] Full verify gate"
npm run verify
echo

echo "P-D5 PASS"
