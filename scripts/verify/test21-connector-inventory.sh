#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-21: Legacy connector inventory gate (G4.1)"
echo

echo "[1/2] Inventory contract checker"
"${python_bin}" scripts/verify/check_legacy_connector_inventory.py
echo

echo "[2/2] Inventory unit tests"
"${python_bin}" -m unittest tests.test_legacy_connector_inventory -v
echo

echo "TEST-21 PASS"
