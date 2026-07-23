"""Disposable worktree isolation for continuous workers (Gate 3)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.safe_improvement.isolated_executor import (
    IsolationError,
    agent_workspace_for_isolation,
    cleanup_isolation_root,
    create_isolation_root,
    read_baseline_metadata,
)
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root


def stage_task_attachments(
    *,
    task: dict[str, Any],
    agent_root: Path,
) -> list[str]:
    """Copy scoped chat attachments into the worker isolation as read-only inputs."""
    from app.persistence import attachment_store

    attachment_ids = task.get("attachment_ids")
    if not isinstance(attachment_ids, list) or not attachment_ids:
        return []

    target_dir = agent_root / ".axon-attachments"
    target_dir.mkdir(parents=True, exist_ok=True)
    staged: list[str] = []
    for attachment_id in attachment_ids:
        clean_id = str(attachment_id or "").strip()
        if not clean_id:
            continue
        record = attachment_store.get_attachment(clean_id)
        if record is None:
            continue
        source = Path(str(record.get("storage_path") or ""))
        if not source.is_file():
            continue
        filename = str(record.get("filename") or source.name).strip() or source.name
        destination = target_dir / f"{clean_id}_{filename}"
        destination.write_bytes(source.read_bytes())
        try:
            destination.chmod(0o400)
        except OSError:
            pass
        staged.append(str(destination))
    return staged


def create_worker_isolation(*, workspace_id: str, run_id: str) -> Path:
    """Create a disposable checkout for one continuous-worker run."""
    bound = resolve_workspace_root(workspace_id)
    return create_isolation_root(proposal_id=run_id, bound_project_root=bound)


def worker_agent_workspace(isolation_root: Path) -> Path:
    return agent_workspace_for_isolation(isolation_root)


def cleanup_worker_isolation(isolation_root: Path | None) -> dict[str, Any]:
    if isolation_root is None:
        return {"cleaned": False, "removed": False, "kind": "isolation_cleanup"}
    return cleanup_isolation_root(isolation_root)


def isolation_receipt_summary(isolation_root: Path) -> str:
    try:
        meta = read_baseline_metadata(isolation_root)
    except IsolationError:
        return f"worker isolation root {isolation_root}"
    kind = str(meta.get("isolation_kind") or "unknown")
    baseline = str(meta.get("baseline_commit") or "")[:12]
    branch = str(meta.get("worker_branch") or "")
    branch_bit = f" branch={branch}" if branch else ""
    return f"worker isolation {kind}{branch_bit} at {baseline} → {isolation_root}"


__all__ = [
    "IsolationError",
    "WorkspaceRootError",
    "cleanup_worker_isolation",
    "create_worker_isolation",
    "isolation_receipt_summary",
    "stage_task_attachments",
    "worker_agent_workspace",
]
