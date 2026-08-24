#!/usr/bin/env bash
# Ensure a bound workspace has npm dependencies for sandbox borrow (jest, tsc, …).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
source "${repo_root}/scripts/dev/lib/common.sh"

TARGET="${1:-}"
if [[ -z "${TARGET}" ]]; then
  echo "usage: ensure-workspace-toolchain.sh <workspace_id|project_root>" >&2
  exit 1
fi

exec "${repo_root}/scripts/dev/python.sh" - "${TARGET}" "${repo_root}" <<'PY'
import subprocess
import sys
from pathlib import Path

repo_root = Path(sys.argv[2]).resolve()
CONTROL_PLANE = repo_root / "services" / "control-plane"
sys.path.insert(0, str(CONTROL_PLANE))

target = sys.argv[1].strip()
project_root: Path | None = None

if Path(target).expanduser().is_dir():
    project_root = Path(target).expanduser().resolve()
else:
    from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

    try:
        project_root = resolve_workspace_root(target)
    except WorkspaceRootError as exc:
        print(f"ensure-workspace-toolchain: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

package_json = project_root / "package.json"
if not package_json.is_file():
    print(f"ensure-workspace-toolchain: no package.json at {project_root}", file=sys.stderr)
    raise SystemExit(1)

modules = project_root / "node_modules"
jest_bin = modules / ".bin" / "jest"
needs_install = not modules.is_dir() or not any(modules.iterdir()) or not jest_bin.exists()

if needs_install:
    print(f"Installing npm dependencies in {project_root} …")
    completed = subprocess.run(["npm", "ci"], cwd=project_root, check=False)
    if completed.returncode != 0:
        print("npm ci failed; retrying with npm install …")
        completed = subprocess.run(["npm", "install"], cwd=project_root, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
else:
    print(f"node_modules already present at {project_root}")

if jest_bin.exists():
    print(f"jest shim: {jest_bin}")
else:
    print("warn: node_modules/.bin/jest not found — project may not use jest")

print(f"toolchain ready: {project_root}")
PY
