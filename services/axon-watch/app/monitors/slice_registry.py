"""Load and probe workspace monitor slice configs."""

from __future__ import annotations

import json
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _default_config_dir() -> Path:
    return (_repo_root() / "config").resolve()


def list_monitor_slice_paths(config_dir: Path | None = None) -> list[Path]:
    root = config_dir or _default_config_dir()
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob("*-monitor-slice.json") if path.is_file())


def load_monitor_slice(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_monitor_slices(config_dir: Path | None = None) -> list[dict[str, object]]:
    slices: list[dict[str, object]] = []
    for path in list_monitor_slice_paths(config_dir):
        config = load_monitor_slice(path)
        if config:
            config.setdefault("config_path", str(path))
            slices.append(config)
    return slices
