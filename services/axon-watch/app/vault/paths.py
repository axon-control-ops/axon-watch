"""Filesystem paths for Axon-X vault state."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    # paths.py lives at services/axon-watch/app/vault/paths.py → parents[4] is the repo root.
    # parents[3] incorrectly resolves to services/ and created a split-brain vault under
    # services/.local/state whenever AXON_WATCH_STATE_DIR was relative/unset.
    return Path(__file__).resolve().parents[4]


def state_dir() -> Path:
    configured = os.environ.get("AXON_WATCH_STATE_DIR", ".local/state").strip()
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = (repo_root() / path).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def vault_db_path() -> Path:
    return state_dir() / "vault.db"


def vault_import_path() -> Path:
    return state_dir() / "vault-import.json"


def auto_unlock_keyfile_path() -> Path:
    return state_dir() / ".vault_auto_unlock"
