"""Aggregate connector probe results for watch summary surfaces."""

from __future__ import annotations

from copy import deepcopy
import os
import threading
import time

from app.connectors.catalog import load_watch_connector_definitions
from app.connectors.probe import probe_connector
from app.signals.iso_time import utc_now_iso
from app.tunnel.slice_registry import load_tunnel_slice
from app.tunnel.tunnel_probe import probe_cloudflare_tunnel

_CONNECTOR_PROBE_CACHE: dict[str, object] = {
    "loaded_at": 0.0,
    "records": [],
}
_CONNECTOR_PROBE_LOCK = threading.Lock()
_CONNECTOR_REFRESH_LOCK = threading.Lock()
_CONNECTOR_BACKGROUND_REFRESHING = False


def _connector_cache_ttl_seconds() -> float:
    raw = str(os.environ.get("AXON_WATCH_CONNECTOR_CACHE_TTL_SECONDS") or "15").strip()
    try:
        return max(0.0, float(raw))
    except ValueError:
        return 15.0


def reset_connector_probe_cache() -> None:
    with _CONNECTOR_PROBE_LOCK:
        _CONNECTOR_PROBE_CACHE["loaded_at"] = 0.0
        _CONNECTOR_PROBE_CACHE["records"] = []


def store_connector_probe_record(record: dict[str, object]) -> None:
    """Upsert one live probe into the TTL cache, seeding a snapshot when cold."""
    connector_id = str(record.get("connector_id") or "").strip()
    if not connector_id:
        return

    with _CONNECTOR_PROBE_LOCK:
        cached = _CONNECTOR_PROBE_CACHE.get("records")
        needs_seed = not isinstance(cached, list) or not cached

    if needs_seed:
        records = _probe_all_connectors_live()
        with _CONNECTOR_PROBE_LOCK:
            _CONNECTOR_PROBE_CACHE["loaded_at"] = time.monotonic()
            _CONNECTOR_PROBE_CACHE["records"] = deepcopy(records)
            cached = _CONNECTOR_PROBE_CACHE["records"]
    else:
        with _CONNECTOR_PROBE_LOCK:
            cached = _CONNECTOR_PROBE_CACHE.get("records")

    if not isinstance(cached, list):
        return

    next_records: list[dict[str, object]] = []
    replaced = False
    for item in cached:
        if not isinstance(item, dict):
            continue
        if str(item.get("connector_id") or "").strip() == connector_id:
            next_records.append(deepcopy(record))
            replaced = True
        else:
            next_records.append(deepcopy(item))

    if not replaced:
        next_records.append(deepcopy(record))

    with _CONNECTOR_PROBE_LOCK:
        _CONNECTOR_PROBE_CACHE["records"] = next_records
        _CONNECTOR_PROBE_CACHE["loaded_at"] = time.monotonic()


def _probe_all_connectors_live() -> list[dict[str, object]]:
    definitions = load_watch_connector_definitions()
    records = [probe_connector(definition) for definition in definitions.values()]
    tunnel_config = load_tunnel_slice()
    if tunnel_config is not None:
        records.append(probe_cloudflare_tunnel(tunnel_config))
    return records


def _cache_is_fresh(loaded_at: float, now: float, ttl: float, cached: object) -> bool:
    return (
        ttl > 0
        and isinstance(cached, list)
        and loaded_at > 0
        and now - loaded_at < ttl
    )


def _store_connector_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    with _CONNECTOR_PROBE_LOCK:
        _CONNECTOR_PROBE_CACHE["loaded_at"] = time.monotonic()
        _CONNECTOR_PROBE_CACHE["records"] = deepcopy(records)
    return deepcopy(records)


def _refresh_connector_records_locked() -> list[dict[str, object]]:
    records = _probe_all_connectors_live()
    return _store_connector_records(records)


def _start_background_connector_refresh(*, force: bool = False) -> None:
    global _CONNECTOR_BACKGROUND_REFRESHING

    def _runner() -> None:
        global _CONNECTOR_BACKGROUND_REFRESHING
        try:
            with _CONNECTOR_REFRESH_LOCK:
                if force:
                    _refresh_connector_records_locked()
                else:
                    ttl = _connector_cache_ttl_seconds()
                    now = time.monotonic()
                    with _CONNECTOR_PROBE_LOCK:
                        cached = _CONNECTOR_PROBE_CACHE.get("records")
                        loaded_at = float(_CONNECTOR_PROBE_CACHE.get("loaded_at") or 0.0)
                        if _cache_is_fresh(loaded_at, now, ttl, cached):
                            return
                    _refresh_connector_records_locked()
        finally:
            with _CONNECTOR_PROBE_LOCK:
                _CONNECTOR_BACKGROUND_REFRESHING = False

    thread = threading.Thread(
        target=_runner,
        name="axon-watch-connector-probe-refresh",
        daemon=True,
    )
    thread.start()


def probe_all_connectors(*, force: bool = False) -> list[dict[str, object]]:
    global _CONNECTOR_BACKGROUND_REFRESHING
    ttl = _connector_cache_ttl_seconds()
    now = time.monotonic()
    with _CONNECTOR_PROBE_LOCK:
        cached = _CONNECTOR_PROBE_CACHE.get("records")
        loaded_at = float(_CONNECTOR_PROBE_CACHE.get("loaded_at") or 0.0)
        if (
            not force
            and _cache_is_fresh(loaded_at, now, ttl, cached)
        ):
            return deepcopy(cached)  # type: ignore[arg-type]

        stale = deepcopy(cached) if isinstance(cached, list) and cached else None
        if not force and stale is not None:
            if not _CONNECTOR_BACKGROUND_REFRESHING:
                _CONNECTOR_BACKGROUND_REFRESHING = True
                _start_background_connector_refresh()
            return stale

    with _CONNECTOR_REFRESH_LOCK:
        now = time.monotonic()
        with _CONNECTOR_PROBE_LOCK:
            cached = _CONNECTOR_PROBE_CACHE.get("records")
            loaded_at = float(_CONNECTOR_PROBE_CACHE.get("loaded_at") or 0.0)
            if not force and _cache_is_fresh(loaded_at, now, ttl, cached):
                return deepcopy(cached)  # type: ignore[arg-type]
            if not force and isinstance(cached, list) and cached:
                return deepcopy(cached)
        return _refresh_connector_records_locked()


def build_connectors_snapshot(items: list[dict[str, object]] | None = None) -> dict[str, object]:
    records = items if items is not None else probe_all_connectors()
    ok_count = sum(1 for item in records if item.get("status") == "ok")
    degraded_count = sum(1 for item in records if item.get("status") == "degraded")
    unavailable_count = sum(1 for item in records if item.get("status") == "unavailable")
    required_unavailable = sum(
        1
        for item in records
        if item.get("required") and item.get("status") != "ok"
    )

    return {
        "configured": len(records),
        "ok": ok_count,
        "degraded": degraded_count,
        "unavailable": unavailable_count,
        "required_unavailable": required_unavailable,
        "items": records,
        "updated_at": utc_now_iso(),
    }
