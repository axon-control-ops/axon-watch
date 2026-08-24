#!/usr/bin/env bash
# Provision npm toolchains + project contracts for every bound workspace.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

exec "${repo_root}/scripts/dev/python.sh" - "${repo_root}" <<'PY'
import sys
from pathlib import Path

repo_root = Path(sys.argv[1]).resolve()
CONTROL_PLANE = repo_root / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE))

from app.workspace_agents.workspace_runtime_bootstrap import provision_workspace_runtime
from app.workspace_project_bindings import load_workspace_project_bindings

bindings = load_workspace_project_bindings()
if not bindings:
    print("No workspace bindings configured.")
    raise SystemExit(0)

print(f"Provisioning {len(bindings)} workspace(s)…")
failed = 0
for workspace_id, binding in sorted(bindings.items()):
    report = provision_workspace_runtime(
        workspace_id,
        project_root=binding.project_root,
        display_name=binding.display_name,
    )
    status = report.get("status")
    host = report.get("host_tools") or {}
    npm = report.get("npm") or {}
    print(
        f"- {workspace_id}: status={status} npm={npm.get('status')} "
        f"host_missing={host.get('missing') or []}"
    )
    if status not in {"ready", "degraded"} or npm.get("status") == "failed":
        failed += 1

raise SystemExit(1 if failed else 0)
PY
