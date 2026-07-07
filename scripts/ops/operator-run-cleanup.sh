#!/usr/bin/env bash
# Bulk-complete stale operator runs (verification debt, demo workspaces, one-shot commands).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CP="${AXON_WATCH_CONTROL_PLANE_BASE:-http://127.0.0.1:8787}"

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

python3 - "$CP" "$DRY_RUN" <<'PY'
import json
import sys
import urllib.error
import urllib.request

base = sys.argv[1].rstrip("/")
dry_run = sys.argv[2] == "1"

DEMO_WORKSPACES = {
    "workspace_smoke",
    "workspace_recsys",
    "workspace_finance",
    "workspace_nlp",
    "workspace_cv",
    "workspace_edge",
    "workspace_research",
    "workspace_alpha",
    "workspace_bootstrap",
}

ONE_SHOT_SUMMARIES = {
    "git status",
    "health",
    "api/health",
    "runtime/summary",
    "ls",
    "list files",
    "dir",
    "check-health",
    "check health",
    "read readme.md",
}


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{base}{path}", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def post(path: str) -> dict:
    request = urllib.request.Request(
        f"{base}{path}",
        method="POST",
        headers={"Content-Type": "application/json"},
        data=b"{}",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def should_complete(run: dict) -> tuple[bool, str]:
    phase = str(run.get("phase", ""))
    if phase in {"completed", "failed", "cancelled"}:
        return False, ""
    workspace_id = str(run.get("workspace_id", ""))
    summary = str(run.get("summary", "")).strip().lower()
    if workspace_id in DEMO_WORKSPACES:
        return True, "demo workspace"
    if phase == "review_ready":
        if summary in ONE_SHOT_SUMMARIES or summary.startswith("read ") or summary.startswith("cat "):
            return True, "one-shot review_ready"
        return True, "review_ready backlog"
    if phase in {"executing", "paused"} and workspace_id in DEMO_WORKSPACES:
        return True, "demo zombie"
    if phase == "executing" and summary in ONE_SHOT_SUMMARIES:
        return True, "one-shot executing zombie"
    return False, ""


payload = get("/api/runs")
targets = []
for run in payload.get("items", []):
    ok, reason = should_complete(run)
    if ok:
        targets.append((run, reason))

print(f"Found {len(targets)} run(s) to complete")
for run, reason in targets:
    print(f"  - {run['run_id']} [{run['workspace_id']}] phase={run['phase']} summary={run.get('summary','')!r} ({reason})")

if dry_run:
    print("Dry run — no changes made.")
    sys.exit(0)

completed = 0
errors = 0
for run, _reason in targets:
    run_id = run["run_id"]
    try:
        post(f"/api/runs/{run_id}/complete")
        completed += 1
    except urllib.error.HTTPError as exc:
        errors += 1
        print(f"FAILED {run_id}: HTTP {exc.code}", file=sys.stderr)

print(f"Completed {completed} run(s); {errors} error(s)")
PY
