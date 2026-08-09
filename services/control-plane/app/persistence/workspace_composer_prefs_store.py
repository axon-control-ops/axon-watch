"""Per-workspace Agent Dock composer model prefs (server-side for workers)."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from app.cli_runtime.model_policy import normalize_model_id
from app.persistence import run_store_sqlite

_VALID_RUNTIME_FAMILIES = {"cursor", "claude", "codex"}
_MAX_CONCURRENT_RUNTIMES_CEILING = 8


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


def default_prefs() -> dict[str, Any]:
    return {
        "cursor_cli_model": "auto",
        "runtime_target": "",
        "auto_allowed_runtimes": [],
        "max_concurrent_runtimes": 1,
        "updated_at": None,
    }


def _normalize_auto_allowed_runtimes(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [r for r in raw if isinstance(r, str) and r.strip() in _VALID_RUNTIME_FAMILIES]


def _normalize_max_concurrent_runtimes(raw: Any) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    return max(1, min(_MAX_CONCURRENT_RUNTIMES_CEILING, value))


def get_workspace_composer_prefs(workspace_id: str) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        return default_prefs()
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT cursor_cli_model, runtime_target,
                   auto_allowed_runtimes_json, max_concurrent_runtimes,
                   updated_at
            FROM workspace_composer_prefs
            WHERE workspace_id = ?
            """,
            (cleaned,),
        ).fetchone()
    if not row:
        return default_prefs()
    model = normalize_model_id(row["cursor_cli_model"]) or "auto"
    try:
        raw_runtimes = json.loads(row["auto_allowed_runtimes_json"] or "[]")
    except (TypeError, ValueError):
        raw_runtimes = []
    return {
        "cursor_cli_model": model if model else "auto",
        "runtime_target": str(row["runtime_target"] or "").strip(),
        "auto_allowed_runtimes": _normalize_auto_allowed_runtimes(raw_runtimes),
        "max_concurrent_runtimes": _normalize_max_concurrent_runtimes(row["max_concurrent_runtimes"]),
        "updated_at": row["updated_at"],
    }


def set_workspace_composer_prefs(
    workspace_id: str,
    *,
    cursor_cli_model: str | None = None,
    runtime_target: str | None = None,
    auto_allowed_runtimes: list[str] | None = None,
    max_concurrent_runtimes: int | None = None,
) -> dict[str, Any]:
    cleaned = str(workspace_id or "").strip()
    if not cleaned:
        raise ValueError("workspace_id is required")
    current = get_workspace_composer_prefs(cleaned)
    next_model = current["cursor_cli_model"]
    if cursor_cli_model is not None:
        next_model = normalize_model_id(cursor_cli_model) or "auto"
    next_runtime_target = current["runtime_target"]
    if runtime_target is not None:
        next_runtime_target = str(runtime_target or "").strip()
    next_allowed = current["auto_allowed_runtimes"]
    if auto_allowed_runtimes is not None:
        next_allowed = _normalize_auto_allowed_runtimes(auto_allowed_runtimes)
    next_concurrent = current["max_concurrent_runtimes"]
    if max_concurrent_runtimes is not None:
        next_concurrent = _normalize_max_concurrent_runtimes(max_concurrent_runtimes)
    updated_at = _utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_composer_prefs (
                workspace_id, cursor_cli_model, runtime_target,
                auto_allowed_runtimes_json, max_concurrent_runtimes, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_id) DO UPDATE SET
                cursor_cli_model = excluded.cursor_cli_model,
                runtime_target = excluded.runtime_target,
                auto_allowed_runtimes_json = excluded.auto_allowed_runtimes_json,
                max_concurrent_runtimes = excluded.max_concurrent_runtimes,
                updated_at = excluded.updated_at
            """,
            (cleaned, next_model, next_runtime_target, json.dumps(next_allowed), next_concurrent, updated_at),
        )
        connection.commit()
    return {
        "cursor_cli_model": next_model,
        "runtime_target": next_runtime_target,
        "auto_allowed_runtimes": next_allowed,
        "max_concurrent_runtimes": next_concurrent,
        "updated_at": updated_at,
    }


def resolve_worker_runtime_model(workspace_id: str) -> str | None:
    """Model workers may pass into Lane B.

    Auto → None (omit --model). Composer or explicit API pin → that id.
    """
    prefs = get_workspace_composer_prefs(workspace_id)
    model = normalize_model_id(prefs.get("cursor_cli_model"))
    if not model or model.lower() == "auto":
        return None
    return model


def resolve_worker_runtime_target(workspace_id: str) -> str | None:
    """Runtime family (e.g. ``claude_local``) workers should dispatch through.

    Mirrors the operator's Agent Dock runtime-target pick so continuous/fleet
    workers don't silently fall back to the server's default runtime.
    """
    try:
        from app.persistence import operator_presence_settings_store

        settings = operator_presence_settings_store.load_settings()
        if (
            bool(settings.get("auto_composer_runtime_override_enabled"))
            and str(settings.get("autonomy_mode") or "").strip().lower() == "full"
        ):
            override = str(settings.get("auto_composer_runtime_target") or "").strip()
            if override:
                return override
    except Exception:
        pass

    prefs = get_workspace_composer_prefs(workspace_id)
    target = str(prefs.get("runtime_target") or "").strip()
    return target or None
