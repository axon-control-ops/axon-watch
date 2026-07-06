"""Persisted operator presence settings for persona and alert preferences."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.persistence import run_store_sqlite
from app.spoken_alert_policy import default_operator_presence_settings

_SETTINGS_KEY = "default"


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


def _normalize_settings(raw: dict[str, Any] | None) -> dict[str, bool | str]:
    defaults = default_operator_presence_settings()
    if not raw:
        return defaults
    normalized = dict(defaults)
    for key in defaults:
        if key not in raw:
            continue
        if key == "kairo_narration":
            value = str(raw[key] or defaults[key]).strip().lower()
            if value in {"off", "minimal", "conversational"}:
                normalized[key] = value
            continue
        normalized[key] = bool(raw[key])
    return normalized


def reset_store() -> None:
    with _managed_connection() as connection:
        connection.execute("DELETE FROM operator_presence_settings")
        connection.commit()


def load_settings() -> dict[str, bool]:
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT settings_json FROM operator_presence_settings WHERE settings_key = ?",
            (_SETTINGS_KEY,),
        ).fetchone()
    if row is None:
        return default_operator_presence_settings()
    payload = json.loads(str(row["settings_json"]))
    if not isinstance(payload, dict):
        return default_operator_presence_settings()
    return _normalize_settings(payload)


def save_settings(settings: dict[str, Any]) -> dict[str, object]:
    normalized = _normalize_settings(settings)
    updated_at = _utc_now_iso()
    payload = json.dumps(normalized)
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO operator_presence_settings (settings_key, settings_json, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(settings_key) DO UPDATE SET
                settings_json = excluded.settings_json,
                updated_at = excluded.updated_at
            """,
            (_SETTINGS_KEY, payload, updated_at),
        )
        connection.commit()
    return {"settings": deepcopy(normalized), "updated_at": updated_at}
