#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-22: Tunnel remote control gate (G4.3)"
echo

echo "[1/3] Tunnel slice unit tests"
PYTHONPATH=services/axon-watch "${python_bin}" -m unittest \
  tests.test_tunnel_remote_control \
  -v
echo

echo "[2/3] Control-plane tunnel proxy tests"
"${python_bin}" -m unittest tests.test_control_plane_tunnel -v
echo

echo "[3/3] Connector inventory still includes tunnel row"
"${python_bin}" scripts/verify/check_legacy_connector_inventory.py
echo

echo "TEST-22 PASS"
