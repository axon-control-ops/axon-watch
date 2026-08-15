"""Lifecycle cleanup for run-scoped agent sandbox state."""

from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path

from app.cli_runtime.agent_sandbox import default_policy_root

_STALE_AFTER_SECONDS = 2 * 60 * 60
_MAX_RETAINED_POLICIES = 32


def _policy_path(run_id: str, *, policy_root: Path | None = None) -> Path | None:
    clean_run_id = str(run_id or "").strip()
    if not clean_run_id:
        return None
    identity = hashlib.sha256(clean_run_id.encode("utf-8")).hexdigest()[:24]
    return (policy_root or default_policy_root()) / f"run-{identity}"


def _remove_policy_tree(target: Path, *, root: Path) -> bool:
    try:
        if not target.exists():
            return False
        resolved_root = root.expanduser().resolve(strict=False)
        resolved_target = target.expanduser().resolve(strict=False)
        if target.is_symlink() or resolved_target.parent != resolved_root:
            return False
        for current, directories, _files in os.walk(resolved_target, topdown=False):
            for directory in directories:
                child = Path(current) / directory
                if not child.is_symlink():
                    child.chmod(0o700)
            Path(current).chmod(0o700)
        shutil.rmtree(resolved_target)
        return True
    except Exception:
        return False


def cleanup_run_sandbox(run_id: str, *, policy_root: Path | None = None) -> bool:
    """Remove one completed run's private HOME, hooks, caches, and scratch state."""
    root = policy_root or default_policy_root()
    target = _policy_path(run_id, policy_root=root)
    return bool(target and _remove_policy_tree(target, root=root))


def prune_stale_run_sandboxes(
    *,
    policy_root: Path | None = None,
    now: float | None = None,
    stale_after_seconds: int = _STALE_AFTER_SECONDS,
    max_retained: int = _MAX_RETAINED_POLICIES,
) -> int:
    """Bound crash leftovers without touching the newest likely-active policies."""
    root = policy_root or default_policy_root()
    if not root.is_dir() or root.is_symlink():
        return 0
    cutoff = (time.time() if now is None else now) - max(0, stale_after_seconds)
    candidates: list[tuple[Path, float]] = []
    for child in root.iterdir():
        try:
            if child.name.startswith("run-") and child.is_dir() and not child.is_symlink():
                candidates.append((child, child.stat().st_mtime))
        except OSError:
            continue
    candidates.sort(key=lambda item: item[1], reverse=True)
    removed = 0
    for index, (child, modified_at) in enumerate(candidates):
        if index < max(0, max_retained) and modified_at >= cutoff:
            continue
        removed += int(_remove_policy_tree(child, root=root))
    return removed


__all__ = ["cleanup_run_sandbox", "prune_stale_run_sandboxes"]
