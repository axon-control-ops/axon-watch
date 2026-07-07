#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${repo_root}"

source "${repo_root}/scripts/dev/lib/common.sh"
load_env
"${repo_root}/scripts/dev/ensure-python-deps.sh"
python_bin="$(resolve_python "${repo_root}")"

echo "TEST-25: Connector parity bundle gate (G4.6)"
echo

echo "[1/6] Restart watch + control-plane to load connector routes"
if [[ -f "$(service_pid_file "axon-watch")" ]]; then
  stop_service "control-plane"
  stop_service "axon-watch"
  start_service \
    "axon-watch" \
    "${repo_root}/services/axon-watch" \
    "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_WATCH_SERVICE_PORT}"
  wait_for_http \
    "axon-watch" \
    "$(service_ready_url "axon-watch")" \
    30 \
    "$(service_pid_file "axon-watch")"
  start_service \
    "control-plane" \
    "${repo_root}/services/control-plane" \
    "${python_bin}" -m uvicorn app.main:app --host 127.0.0.1 --port "${AXON_WATCH_CONTROL_PLANE_PORT}"
  wait_for_http \
    "control-plane" \
    "$(service_ready_url "control-plane")" \
    30 \
    "$(service_pid_file "control-plane")"
fi
echo

echo "[2/6] Dev stack health"
./scripts/dev/check-health.sh
echo

echo "[3/6] Watch connector slices (TEST-3 steps 2-4)"
"${python_bin}" -m unittest tests.test_watch_connectors -v
"${python_bin}" -m unittest tests.test_control_plane_connectors -v
"${python_bin}" -m unittest tests.test_test3_watch_connectors_acceptance -v
"${python_bin}" -m unittest tests.test_control_plane_watch_integration -v
echo

echo "[4/6] Legacy connector inventory (G4.1)"
./scripts/verify/test21-connector-inventory.sh
echo

echo "[5/6] Tunnel + voice + dock parity (G4.3-G4.5)"
./scripts/verify/test22-tunnel-remote-control.sh
./scripts/verify/test23-voice-cockpit.sh
./scripts/verify/test24-agent-dock-parity.sh
echo

echo "[6/6] Inventory documents bundled gates"
"${python_bin}" - <<'PY'
import json
from pathlib import Path

repo = Path(".")
inventory = json.loads((repo / "config/legacy-connector-inventory.json").read_text(encoding="utf-8"))
required_g4_gates = {
    "verify:tunnel-remote-control",
    "verify:voice-cockpit",
    "verify:agent-dock-parity",
}
gates = {entry.get("probe", {}).get("gate") for entry in inventory["inventory"]}
missing = sorted(g for g in required_g4_gates if g not in gates)
if missing:
    raise SystemExit(f"inventory missing G4 gate references: {missing}")
print("  ok G4.3-G4.5 gates referenced in legacy-connector-inventory.json")
PY
echo

echo "TEST-25 PASS"
