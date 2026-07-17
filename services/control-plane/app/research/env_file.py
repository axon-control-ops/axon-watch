"""Load missing research-related keys from the repo-root .env file.

Cursor launches the research MCP with a minimal env block, so process env alone
often lacks AXON_WATCH_GOOGLE_CSE_*. Fill gaps from the gitignored local .env
without overriding values already present in the environment.
"""

from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_repo_env_file(*, force: bool = False) -> None:
    """Populate os.environ from repo-root .env for keys that are unset/blank."""

    global _LOADED
    if _LOADED and not force:
        return
    _LOADED = True

    path = _repo_root() / ".env"
    if not path.is_file():
        return

    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or not key.replace("_", "").isalnum():
            continue
        value = value.split("#", 1)[0].strip().strip('"').strip("'")
        current = str(os.environ.get(key, "")).strip()
        if current:
            continue
        if value:
            os.environ[key] = value
