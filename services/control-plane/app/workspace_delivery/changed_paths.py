"""Discover worker-authored paths, including explicitly scoped ignored files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from app.workspace_agents.diff_policy import is_control_plane_owned_path


def list_changed_paths(
    isolation_root: Path,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]],
    include_ignored_pathspecs: list[str] | None = None,
) -> list[str]:
    paths: list[str] = []
    for args in (
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        result = run(args, cwd=isolation_root)
        if result.returncode == 0:
            _append_paths(paths, result.stdout or "")
    allowed = [
        str(path).strip().lstrip("./")
        for path in (include_ignored_pathspecs or [])
        if str(path).strip().lstrip("./")
    ]
    if allowed:
        result = run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", *allowed],
            cwd=isolation_root,
        )
        if result.returncode == 0:
            _append_paths(paths, result.stdout or "")
    return paths


def _append_paths(paths: list[str], output: str) -> None:
    for line in output.splitlines():
        cleaned = line.strip()
        if cleaned and cleaned not in paths and not is_control_plane_owned_path(cleaned):
            paths.append(cleaned)
