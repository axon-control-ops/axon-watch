"""Shared helpers for tests that need a temporary git repository."""

from __future__ import annotations

import subprocess
from pathlib import Path


def init_git_repo(root: Path) -> None:
    """Run git-init and set a deterministic committer identity in *root*."""
    subprocess.run(["git", "init"], cwd=root, capture_output=True, check=False)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        capture_output=True,
        check=False,
    )
    subprocess.run(
        ["git", "config", "user.name", "Axon Test"],
        cwd=root,
        capture_output=True,
        check=False,
    )
