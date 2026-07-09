"""Run bounded DashPro external monitor checks and return signal-ready records."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import time

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


_MONITOR_PROBE_CACHE: dict[str, object] = {
    "loaded_at": 0.0,
    "records": [],
}


def _monitor_cache_ttl_seconds() -> float:
    raw = str(os.environ.get("AXON_WATCH_MONITOR_CACHE_TTL_SECONDS") or "15").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 15.0


def reset_monitor_probe_cache() -> None:
    _MONITOR_PROBE_CACHE["loaded_at"] = 0.0
    _MONITOR_PROBE_CACHE["records"] = []


def probe_dashpro_monitor_records() -> list[dict[str, object]]:
    config = load_monitor_config()
    return probe_monitor_slice(config)


def probe_monitor_records() -> list[dict[str, object]]:
    ttl = _monitor_cache_ttl_seconds()
    cached = _MONITOR_PROBE_CACHE.get("records")
    loaded_at = float(_MONITOR_PROBE_CACHE.get("loaded_at") or 0.0)
    now = time.monotonic()
    if ttl > 0 and isinstance(cached, list) and loaded_at > 0 and now - loaded_at < ttl:
        return deepcopy(cached)

    records = probe_all_monitor_slices()
    _MONITOR_PROBE_CACHE["loaded_at"] = time.monotonic()
    _MONITOR_PROBE_CACHE["records"] = deepcopy(records)
    return records
