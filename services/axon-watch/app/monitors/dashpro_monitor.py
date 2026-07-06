"""Run bounded DashPro external monitor checks and return signal-ready records."""

from __future__ import annotations

from pathlib import Path

from app.monitors.monitor_probe import probe_all_monitor_slices, probe_monitor_slice
from app.monitors.slice_registry import load_monitor_slice


def _service_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _repo_root() -> Path:
    return _service_root().parent.parent


def _default_config_path() -> Path:
    return (_repo_root() / "config" / "dashpro-monitor-slice.json").resolve()


def load_monitor_config(path: Path | None = None) -> dict[str, object]:
    return load_monitor_slice(path or _default_config_path())


def probe_dashpro_monitor_records() -> list[dict[str, object]]:
    config = load_monitor_config()
    return probe_monitor_slice(config)


def probe_monitor_records() -> list[dict[str, object]]:
    return probe_all_monitor_slices()
