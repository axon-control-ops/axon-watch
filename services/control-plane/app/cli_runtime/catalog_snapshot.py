"""CLI runtime status snapshot cache and probe assembly."""

from __future__ import annotations

import copy
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any

from app.cli_runtime.auth_probes import (
    codex_auth_status as _codex_auth_status,
    cursor_auth_status as _cursor_auth_status,
    vault_auth_overlay as _vault_auth_overlay,
)
from app.cli_runtime.cursor_usage_probe import probe_cursor_usage
from app.cli_runtime.vault_keys import fetch_runtime_context

StatusRecord = dict[str, Any]

_SNAPSHOT_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_CACHE_TTL_SECONDS = 30.0
_SNAPSHOT_BUILD_LOCK = threading.Lock()
_SNAPSHOT_REFRESH_THREAD: threading.Thread | None = None
_SNAPSHOT_REFRESH_LOCK = threading.Lock()


def invalidate_runtime_snapshot_cache() -> None:
    _SNAPSHOT_CACHE["fetched_at"] = 0.0
    _SNAPSHOT_CACHE["payload"] = None


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


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truthy_env(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _local_runtime_record(
    runtime_id: str,
    *,
    family: str,
    binary: str,
    auth: StatusRecord,
    label: str,
) -> StatusRecord:
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "local",
        "available": bool(binary),
        "binary": binary,
        "auth": auth,
        "ready": bool(binary) and bool(auth.get("logged_in")),
        "mode_support": ["ask", "plan", "agent", "debug"],
    }


def _cloud_runtime_record(
    runtime_id: str,
    *,
    family: str,
    label: str,
    vault_posture: dict[str, Any],
    env_keys: dict[str, str],
) -> StatusRecord:
    enabled = _truthy_env(os.environ.get(f"AXON_WATCH_{runtime_id.upper()}_ENABLED"))
    auth = _vault_auth_overlay(runtime_id, vault_posture=vault_posture, env_keys=env_keys) or {
        "logged_in": False,
        "auth_method": "",
        "provider_label": label,
        "vault_posture": vault_posture.get("posture"),
        "message": "Cloud runtime not configured yet in Axon-X." if not enabled else "Cloud runtime flagged as enabled.",
    }
    if enabled and auth.get("logged_in"):
        auth = {
            **auth,
            "auth_method": "vault_api_key",
            "message": "Cloud runtime enabled with vault-fed credentials.",
        }
    ready = bool(enabled) and bool(auth.get("logged_in"))
    if enabled and not auth.get("logged_in") and vault_posture.get("unlocked"):
        auth = {
            **auth,
            "message": str(
                vault_posture.get("hint")
                or "Cloud runtime enabled but vault keys are missing for this target."
            ),
        }
    return {
        "id": runtime_id,
        "family": family,
        "label": label,
        "target_type": "cloud",
        "available": enabled,
        "binary": "",
        "auth": auth,
        "ready": ready,
        "mode_support": ["ask", "plan", "agent", "debug"],
    }


def _choose_default_runtime(local: list[StatusRecord], cloud: list[StatusRecord]) -> str:
    explicit = str(os.environ.get("AXON_WATCH_IDE_RUNTIME_TARGET", "")).strip().lower()
    known = {record["id"]: record for record in [*local, *cloud]}
    if explicit in known:
        return explicit

    preferred_family = str(os.environ.get("AXON_WATCH_IDE_RUNTIME_FAMILY", "cursor")).strip().lower()
    family_order = [preferred_family, "cursor", "codex"]
    seen: set[str] = set()
    for family in family_order:
        if family in seen:
            continue
        seen.add(family)
        for record in local:
            if record["family"] == family and record["ready"]:
                return str(record["id"])
    for record in local:
        if record["available"]:
            return str(record["id"])
    return "cursor_local"


def runtime_status_snapshot(
    *,
    force_refresh: bool = False,
    allow_stale: bool = False,
) -> StatusRecord:
    from app.cli_runtime.catalog import find_codex_cli, find_cursor_cli

    cached = _SNAPSHOT_CACHE.get("payload")
    fetched_at = float(_SNAPSHOT_CACHE.get("fetched_at") or 0.0)
    cache_fresh = (
        cached is not None and (time.monotonic() - fetched_at) < _CACHE_TTL_SECONDS
    )
    if not force_refresh and cache_fresh:
        return copy.deepcopy(cached)

    # Stale-while-revalidate: never block operator UI on `cursor agent status`.
    # Return last good (or empty) snapshot and rebuild in a background thread.
    if allow_stale and not force_refresh:
        schedule_runtime_status_refresh()
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
        schedule_runtime_status_refresh()
        return copy.deepcopy(cached)

    # Coalesce concurrent bootstrap callers (summary + status + fleet) so CLI
    # auth probes run once per TTL window instead of stacking on the worker pool.
    with _SNAPSHOT_BUILD_LOCK:
        cached = _SNAPSHOT_CACHE.get("payload")
        fetched_at = float(_SNAPSHOT_CACHE.get("fetched_at") or 0.0)
        if (
            not force_refresh
            and cached is not None
            and (time.monotonic() - fetched_at) < _CACHE_TTL_SECONDS
        ):
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
            if key in {"CURSOR_API_KEY", "CODEX_API_KEY", "OPENAI_API_KEY"}
            and value
            and not str(os.environ.get(key, "")).strip()
        }

        cursor_path = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
        codex_path = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())

        local = [
            _local_runtime_record(
                "cursor_local",
                family="cursor",
                binary=cursor_path,
                auth=_cursor_auth_status(
                    cursor_path,
                    vault_posture=vault_posture,
                    env_keys=vault_env_only,
                    probe_env=merged_env,
                ),
                label="Cursor CLI (local)",
            ),
            _local_runtime_record(
                "codex_local",
                family="codex",
                binary=codex_path,
                auth=_codex_auth_status(
                    codex_path,
                    vault_posture=vault_posture,
                    env_keys=vault_env_only,
                    probe_env=merged_env,
                ),
                label="Codex CLI (local)",
            ),
        ]
        cloud = [
            _cloud_runtime_record(
                "cursor_cloud",
                family="cursor",
                label="Cursor Cloud Agent",
                vault_posture=vault_posture,
                env_keys=vault_env_only,
            ),
            _cloud_runtime_record(
                "codex_cloud",
                family="codex",
                label="Codex Cloud Task",
                vault_posture=vault_posture,
                env_keys=vault_env_only,
            ),
        ]
        default_runtime = _choose_default_runtime(local, cloud)

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
