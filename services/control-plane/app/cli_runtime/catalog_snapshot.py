"""CLI runtime status snapshot cache and probe assembly."""

from __future__ import annotations

import copy
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.cli_runtime.catalog_inventory import build_runtime_inventory
from app.cli_runtime.catalog_records import choose_default_runtime
from app.cli_runtime.cursor_usage_probe import probe_cursor_usage
from app.cli_runtime.vault_keys import fetch_runtime_context

StatusRecord = dict[str, Any]

_SNAPSHOT_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = 30.0
_TIMEOUT_CACHE_TTL_SECONDS = 8.0
_SNAPSHOT_BUILD_LOCK = threading.Lock()
_SNAPSHOT_REFRESH_THREAD: threading.Thread | None = None
_SNAPSHOT_REFRESH_LOCK = threading.Lock()
_HEAL_THREAD: threading.Thread | None = None
_HEAL_LOCK = threading.Lock()
_LAST_HEAL_AT = 0.0
_HEAL_COOLDOWN_SECONDS = 45.0


def invalidate_runtime_snapshot_cache() -> None:
    _SNAPSHOT_CACHE["fetched_at"] = 0.0
    _SNAPSHOT_CACHE["payload"] = None


def _auth_message(record: dict[str, Any]) -> str:
    auth = record.get("auth") if isinstance(record, dict) else None
    if not isinstance(auth, dict):
        return ""
    return str(auth.get("message") or "").strip().lower()


def snapshot_has_auth_probe_timeout(payload: dict[str, Any] | None) -> bool:
    if not isinstance(payload, dict):
        return False
    for record in [*(payload.get("local") or []), *(payload.get("cloud") or [])]:
        if not isinstance(record, dict):
            continue
        message = _auth_message(record)
        if "auth probe timed out" in message or "timed out" in message and "auth" in message:
            return True
        provider = str((record.get("auth") or {}).get("provider_label") or "").strip().lower()
        if provider == "timed out":
            return True
    return False


def _cache_ttl_for_payload(payload: dict[str, Any] | None) -> float:
    if snapshot_has_auth_probe_timeout(payload):
        return _TIMEOUT_CACHE_TTL_SECONDS
    return _CACHE_TTL_SECONDS


def schedule_runtime_status_refresh() -> None:
    """Warm/rebuild CLI auth snapshot off the request path (stale-while-revalidate)."""
    global _SNAPSHOT_REFRESH_THREAD
    with _SNAPSHOT_REFRESH_LOCK:
        if _SNAPSHOT_REFRESH_THREAD is not None and _SNAPSHOT_REFRESH_THREAD.is_alive():
            return

        def _worker() -> None:
            try:
                runtime_status_snapshot(force_refresh=True)
            except Exception:
                # Background warm must never raise into the server process.
                return

        _SNAPSHOT_REFRESH_THREAD = threading.Thread(
            target=_worker,
            name="axon-runtime-status-refresh",
            daemon=True,
        )
        _SNAPSHOT_REFRESH_THREAD.start()


def heal_cursor_auth_probe_timeout(*, force: bool = False) -> dict[str, Any] | None:
    """Force-refresh CLI auth when the cached snapshot looks like a probe timeout.

    Returns the refreshed snapshot when a heal ran, otherwise None.
    """
    global _HEAL_THREAD, _LAST_HEAL_AT
    cached = _SNAPSHOT_CACHE.get("payload")
    if not force and not snapshot_has_auth_probe_timeout(
        cached if isinstance(cached, dict) else None
    ):
        return None

    now = time.monotonic()
    with _HEAL_LOCK:
        if not force and (now - _LAST_HEAL_AT) < _HEAL_COOLDOWN_SECONDS:
            schedule_runtime_status_refresh()
            return None
        if _HEAL_THREAD is not None and _HEAL_THREAD.is_alive():
            return None
        _LAST_HEAL_AT = now

        result: dict[str, Any] = {"started": True}

        def _worker() -> None:
            try:
                invalidate_runtime_snapshot_cache()
                runtime_status_snapshot(force_refresh=True)
            except Exception:
                return

        _HEAL_THREAD = threading.Thread(
            target=_worker,
            name="axon-runtime-auth-heal",
            daemon=True,
        )
        _HEAL_THREAD.start()
        return result


def recover_cursor_auth_synchronously() -> dict[str, Any]:
    """Blocking heal for gates that must know whether auth recovered."""
    invalidate_runtime_snapshot_cache()
    return runtime_status_snapshot(force_refresh=True)

def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def runtime_status_snapshot(
    *,
    force_refresh: bool = False,
    allow_stale: bool = False,
) -> StatusRecord:
    cached = _SNAPSHOT_CACHE.get("payload")
    fetched_at = float(_SNAPSHOT_CACHE.get("fetched_at") or 0.0)
    cache_ttl = _cache_ttl_for_payload(cached if isinstance(cached, dict) else None)
    cache_fresh = (
        cached is not None and (time.monotonic() - fetched_at) < cache_ttl
    )
    if not force_refresh and cache_fresh:
        if snapshot_has_auth_probe_timeout(cached if isinstance(cached, dict) else None):
            heal_cursor_auth_probe_timeout()
        return copy.deepcopy(cached)

    # Stale-while-revalidate: never block operator UI on `cursor agent status`.
    # Return last good (or empty) snapshot and rebuild in a background thread.
    if allow_stale and not force_refresh:
        if cached is not None:
            return copy.deepcopy(cached)
        return {
            "updated_at": _utc_now_iso(),
            "default_runtime": "",
            "vault_runtime": {},
            "local": [],
            "cloud": [],
        }

    # Expired cache without allow_stale: still prefer SWR for boot/summary callers
    # that forgot the flag — only force_refresh blocks for a live probe.
    if not force_refresh and cached is not None:
        return copy.deepcopy(cached)

    # Coalesce concurrent bootstrap callers (summary + status + fleet) so CLI
    # auth probes run once per TTL window instead of stacking on the worker pool.
    with _SNAPSHOT_BUILD_LOCK:
        cached = _SNAPSHOT_CACHE.get("payload")
        fetched_at = float(_SNAPSHOT_CACHE.get("fetched_at") or 0.0)
        if (
            not force_refresh
            and cached is not None
            and (time.monotonic() - fetched_at)
            < _cache_ttl_for_payload(cached if isinstance(cached, dict) else None)
        ):
            if snapshot_has_auth_probe_timeout(cached if isinstance(cached, dict) else None):
                heal_cursor_auth_probe_timeout()
            return copy.deepcopy(cached)

        context = fetch_runtime_context(force_refresh=force_refresh)
        vault_posture = dict(context.get("vault_runtime") or {})
        merged_env = dict(os.environ)
        for key, value in dict(context.get("env") or {}).items():
            if not str(merged_env.get(key, "")).strip():
                merged_env[key] = value
        vault_env_only = {
            key: value
            for key, value in merged_env.items()
            if key in {
                "CURSOR_API_KEY",
                "CODEX_API_KEY",
                "OPENAI_API_KEY",
                "ANTHROPIC_API_KEY",
            }
            and value
            and not str(os.environ.get(key, "")).strip()
        }

        local, cloud = build_runtime_inventory(
            vault_posture=vault_posture,
            merged_env=merged_env,
            vault_env_only=vault_env_only,
        )
        default_runtime = choose_default_runtime(local, cloud)

        for record in [*local, *cloud]:
            record["recommended"] = record["id"] == default_runtime

        payload = {
            "updated_at": _utc_now_iso(),
            "default_runtime": default_runtime,
            "vault_runtime": vault_posture,
            "local": local,
            "cloud": cloud,
            "cursor_usage": probe_cursor_usage(force_refresh=force_refresh),
        }
        _SNAPSHOT_CACHE["fetched_at"] = time.monotonic()
        _SNAPSHOT_CACHE["payload"] = copy.deepcopy(payload)
        return copy.deepcopy(payload)
