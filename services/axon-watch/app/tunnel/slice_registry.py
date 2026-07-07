"""Load tunnel slice configuration."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def default_tunnel_slice_path() -> Path:
    configured = os.environ.get("AXON_WATCH_TUNNEL_SLICE_FILE", "").strip()
    if configured:
        path = Path(configured).expanduser()
        if not path.is_absolute():
            path = (_repo_root() / path).resolve()
        return path
    return (_repo_root() / "config" / "tunnel-slice.json").resolve()


def load_tunnel_slice(path: Path | None = None) -> dict[str, object] | None:
    slice_path = path or default_tunnel_slice_path()
    if not slice_path.is_file():
        return None
    try:
        payload = json.loads(slice_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict) or not payload.get("enabled", True):
        return None
    return payload
