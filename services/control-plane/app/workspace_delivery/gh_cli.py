"""Resolve the GitHub CLI binary for draft-PR delivery."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_GH_MISSING_HINT = (
    "gh CLI is required to open a draft PR. "
    "Install GitHub CLI (https://cli.github.com/), put it on PATH for control-plane "
    "(or set AXON_WATCH_GH_CLI_PATH), then run `gh auth login`."
)


def gh_missing_hint() -> str:
    return _GH_MISSING_HINT


def resolve_gh_cli() -> str | None:
    """Return an executable `gh` path, or None when unavailable.

    Order:
    1. ``AXON_WATCH_GH_CLI_PATH`` override
    2. ``PATH`` lookup via ``shutil.which``
    3. Common install locations (user-local, /usr/local, Homebrew)
    """
    override = str(os.environ.get("AXON_WATCH_GH_CLI_PATH") or "").strip()
    if override:
        path = Path(override).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())

    found = shutil.which("gh")
    if found:
        return found

    home = Path.home()
    candidates = (
        home / ".local" / "bin" / "gh",
        Path("/usr/local/bin/gh"),
        Path("/usr/bin/gh"),
        Path("/opt/homebrew/bin/gh"),
        Path("/snap/bin/gh"),
    )
    for candidate in candidates:
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate.resolve())
        except OSError:
            continue
    return None
