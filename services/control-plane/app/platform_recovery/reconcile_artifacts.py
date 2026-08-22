"""Artifact reconcile preview. Default is dry-run. Never delete dirty worktrees."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.platform_recovery.process_inventory import inspect_processes
from app.platform_recovery.projection import build_recovery_center


def preview_reconcile(*, repo_root: str | None = None) -> dict[str, Any]:
    root = Path(repo_root or Path(__file__).resolve().parents[4])
    processes = inspect_processes(repo_root=str(root))
    recovery = build_recovery_center(persist=False)
    stale_pids = [
        row for row in processes if row.get("process") == "test" and row.get("safe_to_terminate")
    ]
    pid_dir = root / ".local" / "pids"
    stale_pid_files: list[str] = []
    if pid_dir.is_dir():
        for path in pid_dir.glob("*.pid"):
            raw = path.read_text(encoding="utf-8", errors="replace").strip()
            if not raw.isdigit() or not Path(f"/proc/{raw}").exists():
                stale_pid_files.append(str(path))
    worktrees = []
    git_worktrees = root / ".git"
    # Report only; never delete.
    return {
        "mode": "DRY_RUN",
        "stale_test_processes": stale_pids,
        "stale_pid_files": stale_pid_files,
        "orphaned_worktrees": worktrees,
        "recovery_attention": recovery.get("attention_count") or 0,
        "items": recovery.get("items") or [],
        "git_present": git_worktrees.exists(),
        "actions": [
            "No filesystem deletes in dry-run.",
            "Worktrees with uncommitted changes require explicit approval.",
        ],
    }


def execute_reconcile(*, repo_root: str | None = None, approve_worktree_delete: bool = False) -> dict[str, Any]:
    preview = preview_reconcile(repo_root=repo_root)
    removed: list[str] = []
    for path in preview.get("stale_pid_files") or []:
        target = Path(str(path))
        try:
            target.unlink(missing_ok=True)
            removed.append(str(target))
        except OSError:
            continue
    if approve_worktree_delete:
        # Explicit no-op until a worktree registry exists. Never invent deletes.
        pass
    preview["mode"] = "EXECUTE"
    preview["removed_pid_files"] = removed
    preview["worktree_deletes"] = []
    return preview
