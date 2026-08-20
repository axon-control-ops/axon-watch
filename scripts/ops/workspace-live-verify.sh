#!/usr/bin/env bash
# Approved wrapper: run workspace-configured live verify commands from the bound root.
# Control plane injects the operator DashPro bridge env before agent dispatch.
set -euo pipefail

WORKSPACE_ID="${AXON_WATCH_WORKSPACE_ID:-${AXON_AGENT_SOURCE_WORKSPACE_ID:-}}"
if [[ -z "$WORKSPACE_ID" ]]; then
  echo "workspace-live-verify: AXON_WATCH_WORKSPACE_ID is required" >&2
  exit 1
fi

ROOT="${AXON_WATCH_REPO_ROOT:-}"
if [[ -z "$ROOT" ]]; then
  ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
fi

exec "$ROOT/scripts/dev/python.sh" - "$WORKSPACE_ID" "$@" <<'PY'
import json
import os
import subprocess
import sys
from pathlib import Path

CONTROL_PLANE = os.environ.get("AXON_WATCH_CONTROL_PLANE_URL", "http://127.0.0.1:8787").rstrip("/")
workspace_id = sys.argv[1]
command = sys.argv[2:] if len(sys.argv) > 2 else ["check-supabase"]

try:
    import urllib.request

    with urllib.request.urlopen(
        f"{CONTROL_PLANE}/api/workspaces/{workspace_id}/service-connection",
        timeout=15,
    ) as response:
        posture = json.loads(response.read().decode("utf-8"))
except OSError as exc:
    print(f"workspace-live-verify: unable to read service connection posture: {exc}", file=sys.stderr)
    sys.exit(1)

if not posture.get("ready"):
    print(posture.get("hint") or "workspace service connection is not ready", file=sys.stderr)
    sys.exit(1)

project_root = Path(str(posture.get("project_root") or "")).expanduser()
if command[0] == "check-supabase":
    argv = ["npm", "run", "check-supabase"]
elif command[0] == "graduation-counts":
    argv = ["npm", "run", "graduation:card-pop-counts"]
else:
    argv = list(command)

completed = subprocess.run(argv, cwd=project_root, check=False)
raise SystemExit(completed.returncode)
PY
