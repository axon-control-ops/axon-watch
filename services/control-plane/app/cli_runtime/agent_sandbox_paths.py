"""Resolve secret paths that must be overlaid inside an agent workspace."""

from __future__ import annotations

import os
from fnmatch import fnmatch
from pathlib import Path

_PRUNED_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv"}


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    return any(
        fnmatch(path, pattern)
        or (pattern.startswith("**/") and fnmatch(path, pattern[3:]))
        for pattern in patterns
    )


def hidden_workspace_paths(
    workspace: Path,
    forbidden_globs: tuple[str, ...],
) -> tuple[Path, ...]:
    """Return existing secret paths plus VCS metadata without following links."""
    hidden: list[Path] = []
    for vcs_name in (".git", ".hg", ".svn"):
        candidate = workspace / vcs_name
        if candidate.exists() or candidate.is_symlink():
            hidden.append(candidate)
    for current, directories, files in os.walk(workspace, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name for name in directories if name not in _PRUNED_DIRS
        ]
        for name in (*directories, *files):
            candidate = current_path / name
            relative = candidate.relative_to(workspace).as_posix()
            if _matches(relative, forbidden_globs):
                hidden.append(candidate)
    return tuple(dict.fromkeys(hidden))


def append_hidden_mounts(arguments: list[str], hidden_paths: tuple[Path, ...]) -> None:
    for path in hidden_paths:
        if path.is_dir() and not path.is_symlink():
            arguments.extend(["--tmpfs", str(path)])
        else:
            arguments.extend(["--ro-bind", "/dev/null", str(path)])


__all__ = ["append_hidden_mounts", "hidden_workspace_paths"]
