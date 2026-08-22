"""Discover worker-authored paths, including explicitly scoped ignored files."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Callable

from app.workspace_agents.diff_policy import is_control_plane_owned_path


def is_borrowed_toolchain_path(isolation_root: Path, relative: str) -> bool:
    """True for a symlink that points outside the checkout.

    Disposable checkouts borrow ``node_modules`` (one symlink per package) and
    local env files from the bound workspace so the toolchain actually runs.
    Those links are infrastructure, never authored work — but git reports each
    one as a change wherever the project does not ignore them. That pushed the
    changed-path count past 1000 and tripped the diff-budget gate, which is why
    delivery began failing with "changed path count 1012 exceeds budget 120".

    Filtering here rather than at each caller is deliberate: delivery, the
    verifier contract, and the composer review all read through this function,
    and only one of them had a local filter.
    """
    candidate = isolation_root / relative
    try:
        if not candidate.is_symlink():
            return False
        return not candidate.resolve().is_relative_to(isolation_root.resolve())
    except (OSError, ValueError):
        return False


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
    # Do not turn a directory-wide task allowance into a claim over every
    # ignored file already present there. Sandboxes may bind historical report
    # directories into the checkout, including private artifacts unrelated to
    # the current run. Ignored deliverables must therefore be scoped by exact
    # file path; normal tracked and unignored files are still discovered above.
    allowed = [
        cleaned
        for path in (include_ignored_pathspecs or [])
        if (cleaned := str(path).strip().lstrip("./"))
        and not cleaned.endswith("/")
        and not (isolation_root / cleaned).is_dir()
    ]
    if allowed:
        result = run(
            ["git", "ls-files", "--others", "--ignored", "--exclude-standard", "--", *allowed],
            cwd=isolation_root,
        )
        if result.returncode == 0:
            _append_paths(paths, result.stdout or "")
    return [path for path in paths if not is_borrowed_toolchain_path(isolation_root, path)]


def _append_paths(paths: list[str], output: str) -> None:
    for line in output.splitlines():
        cleaned = line.strip()
        if cleaned and cleaned not in paths and not is_control_plane_owned_path(cleaned):
            paths.append(cleaned)
