#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-23: Voice cockpit event-driven presence gate (G4.4)"
echo

echo "[1/4] Voice cockpit unit tests"
npm run test -w @axon-watch/console-web -- \
  src/features/voice-deck/voice-cockpit-presence.test.ts \
  src/lib/live-events-session.test.ts
echo

echo "[2/4] Python slice wiring tests"
"${python_bin}" -m unittest tests.test_g4_voice_cockpit_and_dock.VoiceCockpitSliceTests -v
echo

echo "[3/4] Spoken alert + voice deck regression"
"${python_bin}" -m unittest tests.test_parity_d5_voice_deck -v
npm run test -w @axon-watch/console-web -- \
  src/features/voice-deck/voice-deck.test.ts \
  src/lib/spoken-alert-delivery.test.ts
echo

echo "[4/4] Live events regression"
"${python_bin}" -m unittest tests.test_control_plane_live_events -v
echo

echo "TEST-23 PASS"
