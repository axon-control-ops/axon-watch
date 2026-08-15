"""Persisted fleet / continuous-worker scheduler controls (UI overlay)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.persistence import run_store_sqlite

_SETTINGS_KEY = "default"
_MAX_ACTIVE_CEILING = 16
_MAX_STARTS_CEILING = 8


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def default_settings() -> dict[str, Any]:
    # Safe default: action-taking continuous workers stay off until an
    # operator enables them in UI. Observation stays on: company watchers are
    # smoke alarms, not autonomous actors.
    return {
        "watcher_scheduler_enabled": True,
        "scheduler_enabled": False,
        "max_active": 4,
        "max_starts_per_tick": 2,
        "employee_enabled": {},
    }


def employee_enabled_key(workspace_id: str, role: str) -> str:
    return f"{workspace_id.strip()}:{role.strip().lower()}"


def _normalize_employee_enabled(raw: Any) -> dict[str, bool]:
    if not isinstance(raw, dict):
        return {}
    normalized: dict[str, bool] = {}
    for key, value in raw.items():
        cleaned = str(key or "").strip()
        if not cleaned or ":" not in cleaned:
            continue
        normalized[cleaned] = bool(value)
    return normalized


def _clamp_int(raw: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, value))


def _normalize_settings(raw: dict[str, Any] | None) -> dict[str, Any]:
    defaults = default_settings()
    if not raw:
        return deepcopy(defaults)
    return {
        "watcher_scheduler_enabled": bool(
            raw.get(
                "watcher_scheduler_enabled",
                defaults["watcher_scheduler_enabled"],
            )
        ),
        "scheduler_enabled": bool(raw.get("scheduler_enabled", defaults["scheduler_enabled"])),
        "max_active": _clamp_int(
            raw.get("max_active", defaults["max_active"]),
            default=int(defaults["max_active"]),
            minimum=1,
            maximum=_MAX_ACTIVE_CEILING,
        ),
        "max_starts_per_tick": _clamp_int(
            raw.get("max_starts_per_tick", defaults["max_starts_per_tick"]),
            default=int(defaults["max_starts_per_tick"]),
            minimum=1,
            maximum=_MAX_STARTS_CEILING,
        ),
        "employee_enabled": _normalize_employee_enabled(raw.get("employee_enabled")),
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM worker_scheduler_settings")
        connection.commit()


def load_settings() -> dict[str, Any]:
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT settings_json, updated_at
            FROM worker_scheduler_settings
            WHERE settings_key = ?
            """,
            (_SETTINGS_KEY,),
        ).fetchone()
    if row is None:
        return default_settings()
    payload = json.loads(str(row["settings_json"]))
    if not isinstance(payload, dict):
        return default_settings()
    normalized = _normalize_settings(payload)
    updated_at = str(row["updated_at"] or "").strip()
    if updated_at:
        normalized["updated_at"] = updated_at
    return normalized


def save_settings(settings: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_settings(settings)
    updated_at = _utc_now_iso()
    payload = json.dumps(normalized)
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO worker_scheduler_settings (settings_key, settings_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(settings_key) DO UPDATE SET
              settings_json = excluded.settings_json,
              updated_at = excluded.updated_at
            """,
            (_SETTINGS_KEY, payload, updated_at),
        )
        connection.commit()
    result = dict(normalized)
    result["updated_at"] = updated_at
    return result


def patch_settings(patch: dict[str, Any]) -> dict[str, Any]:
    current = load_settings()
    if "watcher_scheduler_enabled" in patch and patch["watcher_scheduler_enabled"] is not None:
        current["watcher_scheduler_enabled"] = bool(patch["watcher_scheduler_enabled"])
    if "scheduler_enabled" in patch and patch["scheduler_enabled"] is not None:
        current["scheduler_enabled"] = bool(patch["scheduler_enabled"])
    if "max_active" in patch and patch["max_active"] is not None:
        current["max_active"] = patch["max_active"]
    if "max_starts_per_tick" in patch and patch["max_starts_per_tick"] is not None:
        current["max_starts_per_tick"] = patch["max_starts_per_tick"]
    if "employee_enabled" in patch and isinstance(patch["employee_enabled"], dict):
        merged = dict(current.get("employee_enabled") or {})
        for key, value in patch["employee_enabled"].items():
            cleaned = str(key or "").strip()
            if not cleaned:
                continue
            merged[cleaned] = bool(value)
        current["employee_enabled"] = merged
    return save_settings(current)


def is_employee_enabled(workspace_id: str, role: str, *, file_enabled: bool = True) -> bool:
    if not file_enabled:
        return False
    settings = load_settings()
    overlay = settings.get("employee_enabled") or {}
    key = employee_enabled_key(workspace_id, role)
    if key in overlay:
        return bool(overlay[key])
    return True
