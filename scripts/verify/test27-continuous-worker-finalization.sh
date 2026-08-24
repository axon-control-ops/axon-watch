#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-27: Continuous worker finalization regression gate"
echo

echo "[1/2] Worker finalization regression coverage"
PYTHONPATH=services/control-plane "${python_bin}" -m unittest \
  tests.test_fleet_self_heal_gate6_enforcement \
  -v
echo

echo "TEST-27 PASS"
