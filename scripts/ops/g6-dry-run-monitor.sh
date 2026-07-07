#!/usr/bin/env bash
# Append Phase G6 dry-run snapshots to docs/PHASE_G6_DRY_RUN_AUDIT_LOG.md
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LOG="${ROOT}/docs/PHASE_G6_DRY_RUN_AUDIT_LOG.md"
CP="${AXON_WATCH_CONTROL_PLANE_BASE:-http://127.0.0.1:8787}"
TS="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

snapshot() {
  python3 - <<PY
import json, urllib.request
from collections import Counter

cp = "${CP}"
ts = "${TS}"

def get(path):
    try:
        with urllib.request.urlopen(f"{cp}{path}", timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}

runs = get("/api/runs")
items = runs.get("items", []) if isinstance(runs, dict) else []
phases = Counter(r.get("phase") for r in items)
rr = [r for r in items if r.get("phase") == "review_ready"]
ex = [r for r in items if r.get("phase") == "executing"]
brief = get("/api/briefing")

print(f"### Tick {ts}")
print()
print(f"- runs: {len(items)} | phases: {dict(phases)}")
print(f"- review_ready: {len(rr)} | executing: {len(ex)}")
if isinstance(brief, dict):
    print(f"- NOTICE: {brief.get('notice', '')[:120]}")
    print(f"- ADVISE: {brief.get('advise', '')[:120]}")
if ex:
    print("- executing samples:")
    for r in ex[:5]:
        print(f"  - {r.get('run_id','')[:14]} {r.get('workspace_id')} {r.get('summary','')[:24]}")
print()
PY
}

{
  snapshot
} >> "${LOG}"

echo "G6 dry-run tick ${TS} appended to ${LOG}"
