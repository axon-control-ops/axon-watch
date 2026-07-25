"""Run bounded DashPro external monitor checks and return signal-ready records."""

from __future__ import annotations

from copy import deepcopy
import os
from pathlib import Path
import threading
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
_MONITOR_PROBE_LOCK = threading.Lock()
_MONITOR_REFRESH_LOCK = threading.Lock()
_MONITOR_BACKGROUND_REFRESHING = False


def _monitor_cache_ttl_seconds() -> float:
    raw = str(os.environ.get("AXON_WATCH_MONITOR_CACHE_TTL_SECONDS") or "15").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 15.0


def reset_monitor_probe_cache() -> None:
    with _MONITOR_PROBE_LOCK:
        _MONITOR_PROBE_CACHE["loaded_at"] = 0.0
        _MONITOR_PROBE_CACHE["records"] = []


def probe_dashpro_monitor_records() -> list[dict[str, object]]:
    config = load_monitor_config()
    return probe_monitor_slice(config)


def _cache_is_fresh(loaded_at: float, now: float, ttl: float, cached: object) -> bool:
    return (
        ttl > 0
        and isinstance(cached, list)
        and loaded_at > 0
        and now - loaded_at < ttl
    )


def _store_monitor_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    with _MONITOR_PROBE_LOCK:
        _MONITOR_PROBE_CACHE["loaded_at"] = time.monotonic()
        _MONITOR_PROBE_CACHE["records"] = deepcopy(records)
    return deepcopy(records)


def _refresh_monitor_records_locked() -> list[dict[str, object]]:
    records = probe_all_monitor_slices()
    return _store_monitor_records(records)


def _start_background_monitor_refresh() -> None:
    global _MONITOR_BACKGROUND_REFRESHING

    def _runner() -> None:
        global _MONITOR_BACKGROUND_REFRESHING
        try:
            with _MONITOR_REFRESH_LOCK:
                _refresh_monitor_records_locked()
        finally:
            with _MONITOR_PROBE_LOCK:
                _MONITOR_BACKGROUND_REFRESHING = False

    thread = threading.Thread(
        target=_runner,
        name="axon-watch-monitor-probe-refresh",
        daemon=True,
    )
    thread.start()


def probe_monitor_records() -> list[dict[str, object]]:
    global _MONITOR_BACKGROUND_REFRESHING
    ttl = _monitor_cache_ttl_seconds()
    now = time.monotonic()
    with _MONITOR_PROBE_LOCK:
        cached = _MONITOR_PROBE_CACHE.get("records")
        loaded_at = float(_MONITOR_PROBE_CACHE.get("loaded_at") or 0.0)
        if _cache_is_fresh(loaded_at, now, ttl, cached):
            return deepcopy(cached)  # type: ignore[arg-type]

        stale = deepcopy(cached) if isinstance(cached, list) and cached else None
        if stale is not None:
            if not _MONITOR_BACKGROUND_REFRESHING:
                _MONITOR_BACKGROUND_REFRESHING = True
                _start_background_monitor_refresh()
            return stale

    # Cold cache: single-flight the live probe so concurrent inbox polls do not
    # stampede Sentry / IMAP and blow past the control-plane timeout.
    with _MONITOR_REFRESH_LOCK:
        now = time.monotonic()
        with _MONITOR_PROBE_LOCK:
            cached = _MONITOR_PROBE_CACHE.get("records")
            loaded_at = float(_MONITOR_PROBE_CACHE.get("loaded_at") or 0.0)
            if _cache_is_fresh(loaded_at, now, ttl, cached):
                return deepcopy(cached)  # type: ignore[arg-type]
            if isinstance(cached, list) and cached:
                return deepcopy(cached)
        return _refresh_monitor_records_locked()
