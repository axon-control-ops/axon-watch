#!/usr/bin/env bash
# Report whether the control-plane fleet has any non-terminal runs.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
API_BASE="${AXON_CONTROL_PLANE_URL:-http://127.0.0.1:8787}"

python3 - "$API_BASE" <<'PY'
import json
import sys
import urllib.error
import urllib.request

api_base = sys.argv[1].rstrip("/")
url = f"{api_base}/api/runs"

try:
    with urllib.request.urlopen(url, timeout=8) as resp:
        payload = json.load(resp)
except urllib.error.URLError as exc:
    print(f"control-plane unreachable at {url}: {exc}")
    sys.exit(2)

runs = payload if isinstance(payload, list) else payload.get("items") or payload.get("runs") or []
terminal = {"completed", "failed", "cancelled"}
active = [r for r in runs if str(r.get("phase") or "") not in terminal]

print(f"ACTIVE RUNS: {len(active)}")
for row in active[:20]:
    ws = str(row.get("workspace_id") or "")[:22]
    role = str(row.get("employee_role") or "")
    phase = str(row.get("phase") or "")
    run_id = str(row.get("run_id") or "")[:12]
    print(f"  {run_id}  {ws:<22} {role:<12} {phase}")

recent = sorted(
    runs,
    key=lambda r: str(r.get("updated_at") or ""),
    reverse=True,
)[:6]
print()
print("last 6 runs:")
for row in recent:
    ts = str(row.get("updated_at") or "")[:19]
    ws = str(row.get("workspace_id") or "")[:18]
    role = str(row.get("employee_role") or "")
    phase = str(row.get("phase") or "")
    step = str(row.get("current_step") or "")[:48]
    print(f"  {ts} {ws:<18} {role:<9} {phase:<10} {step}")

sys.exit(1 if active else 0)
PY
