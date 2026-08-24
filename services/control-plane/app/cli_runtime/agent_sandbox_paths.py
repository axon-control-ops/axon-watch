"""Resolve secret paths that must be overlaid inside an agent workspace."""

from __future__ import annotations

import os
from fnmatch import fnmatch
from pathlib import Path

_PRUNED_DIRS = {".git", ".hg", ".svn", "node_modules", ".venv", "venv"}
# Only toolchain borrows need bind overlays; .env* symlinks stay hidden/unresolved.
_COMPOSER_BORROW_NAMES = ("node_modules",)


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _unified_borrowed_node_modules(modules: Path) -> Path | None:
    """Return the bound ``node_modules`` tree when checkout entries are all borrows."""
    if modules.is_symlink():
        try:
            target = modules.resolve(strict=True)
        except OSError:
            return None
        return target if target.is_dir() else None
    if not modules.is_dir():
        return None
    try:
        children = list(modules.iterdir())
    except OSError:
        return None
    if not children:
        return None
    source_roots: set[Path] = set()
    for child in children:
        if not child.is_symlink():
            return None
        try:
            target = child.resolve(strict=True)
        except OSError:
            return None
        source_roots.add(target.parent)
    if len(source_roots) != 1:
        return None
    return source_roots.pop()


def _append_escaping_symlink_mount(
    mounts: list[tuple[Path, Path]],
    *,
    root: Path,
    link: Path,
    seen: set[tuple[str, str]],
) -> None:
    if not link.is_symlink():
        return
    try:
        target = link.resolve(strict=True)
    except OSError:
        return
    if _is_relative_to(target, root):
        return
    key = (str(target), str(link))
    if key in seen:
        return
    seen.add(key)
    mounts.append((target, link))


def workspace_outside_symlink_mounts(workspace: Path) -> tuple[tuple[Path, Path], ...]:
    """Symlinks that escape the workspace must be bound so tools work inside bwrap."""
    root = workspace.resolve()
    mounts: list[tuple[Path, Path]] = []
    seen: set[tuple[str, str]] = set()
    modules = root / "node_modules"
    unified = _unified_borrowed_node_modules(modules)
    if unified is not None and not _is_relative_to(unified, root):
        mounts.append((unified, modules))
    elif modules.is_symlink():
        _append_escaping_symlink_mount(mounts, root=root, link=modules, seen=seen)
    # Borrowed .env* files are copied into the checkout (not symlinked) because
    # bubblewrap cannot ro-bind over escaping file symlinks.
    return tuple(mounts)


def append_outside_symlink_binds(arguments: list[str], workspace: Path) -> None:
    """Overlay ro-binds for borrowed checkout symlinks (node_modules)."""
    for target, link_path in workspace_outside_symlink_mounts(workspace):
        arguments.extend(["--ro-bind", str(target), str(link_path)])


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
        # Bubblewrap cannot bind-mount over a symlink ("Can't create file at …").
        # Composer sandboxes link .env* back to the bound root; those targets sit
        # outside the sandbox namespace and are unreachable once /run is tmpfs.
        if path.is_symlink():
            continue
        if path.is_dir():
            arguments.extend(["--tmpfs", str(path)])
        else:
            arguments.extend(["--ro-bind", "/dev/null", str(path)])


__all__ = [
    "append_hidden_mounts",
    "append_outside_symlink_binds",
    "hidden_workspace_paths",
    "workspace_outside_symlink_mounts",
]
