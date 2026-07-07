#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-24: Agent dock parity gate (G4.5)"
echo

echo "[1/4] Dock behavior contract"
"${python_bin}" scripts/verify/check_dock_behavior_contract.py
echo

echo "[2/4] Dock parity unit tests"
npm run test -w @axon-watch/console-web -- \
  src/lib/agent-dock-behavior.test.ts \
  src/lib/dock-seam-layout.test.ts
"${python_bin}" -m unittest tests.test_g4_voice_cockpit_and_dock.AgentDockParitySliceTests -v
echo

echo "[3/4] P-D6 integration slice"
"${python_bin}" -m unittest tests.test_parity_d6_dock_and_startup -v
echo

echo "[4/4] Connector inventory still valid"
"${python_bin}" scripts/verify/check_legacy_connector_inventory.py
echo

echo "TEST-24 PASS"
