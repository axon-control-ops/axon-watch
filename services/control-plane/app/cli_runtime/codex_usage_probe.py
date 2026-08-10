"""Best-effort local Codex CLI usage telemetry.

Codex currently exposes local auth/model state, but not a public account-quota
percentage. This probe is intentionally honest: it surfaces recent local Codex
log activity and any observed usage-limit failure, without pretending to know
the user's subscription quota.
"""

from __future__ import annotations

import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

StatusRecord = dict[str, Any]

_USAGE_CACHE: dict[str, Any] = {"fetched_at": 0.0, "payload": None}
_USAGE_CACHE_TTL_SECONDS = 45.0
_USAGE_LOCK = threading.Lock()

_LIMIT_STATE: dict[str, Any] = {"hit_at": 0.0, "detail": "", "reset_epoch": None}
_LIMIT_LOCK = threading.Lock()
_LIMIT_WINDOW_SECONDS = 5 * 60 * 60
_RESET_EPOCH_RE = re.compile(r"\|\s*(\d{9,13})\b")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _logs_db_path() -> Path | None:
    override = str(os.environ.get("AXON_WATCH_CODEX_LOGS_DB", "")).strip()
    if override:
        path = Path(override).expanduser()
        return path if path.is_file() else None
    for path in (
        Path.home() / ".codex" / "logs_2.sqlite",
        Path.home() / ".codex" / "logs.sqlite",
    ):
        if path.is_file():
            return path
    return None


def _read_local_log_totals() -> dict[str, Any] | None:
    path = _logs_db_path()
    if path is None:
        return None
    conn: sqlite3.Connection | None = None
    try:
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        latest = conn.execute(
            """
            SELECT COUNT(*) AS events, COALESCE(SUM(estimated_bytes), 0) AS bytes,
                   MAX(ts) AS latest_ts
            FROM logs
            """
        ).fetchone()
        recent = conn.execute(
            """
            SELECT COUNT(*) AS events, COALESCE(SUM(estimated_bytes), 0) AS bytes
            FROM logs
            WHERE ts >= ?
            """,
            (int(time.time()) - 24 * 60 * 60,),
        ).fetchone()
        turns = conn.execute(
            """
            SELECT COUNT(*) AS turns
            FROM logs
            WHERE target LIKE '%responses%'
              AND feedback_log_body LIKE '%session_task.turn%'
            """
        ).fetchone()
    except (sqlite3.Error, OSError):
        return None
    finally:
        if conn is not None:
            conn.close()
    latest_record = dict(latest) if latest is not None else {}
    recent_record = dict(recent) if recent is not None else {}
    turns_record = dict(turns) if turns is not None else {}
    latest_ts = latest_record.get("latest_ts")
    return {
        "total_events": int(latest_record.get("events") or 0),
        "total_estimated_bytes": int(latest_record.get("bytes") or 0),
        "events_24h": int(recent_record.get("events") or 0),
        "estimated_bytes_24h": int(recent_record.get("bytes") or 0),
        "turn_events": int(turns_record.get("turns") or 0),
        "latest_log_at": (
            datetime.fromtimestamp(int(latest_ts), tz=timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
            if latest_ts
            else None
        ),
    }


def record_codex_usage_limit_hit(detail: str) -> None:
    match = _RESET_EPOCH_RE.search(detail or "")
    reset_epoch: float | None = None
    if match:
        try:
            raw = int(match.group(1))
            reset_epoch = raw / 1000 if raw > 10_000_000_000 else float(raw)
        except (TypeError, ValueError):
            reset_epoch = None
    with _LIMIT_LOCK:
        _LIMIT_STATE["hit_at"] = time.time()
        _LIMIT_STATE["detail"] = str(detail or "").strip()
        _LIMIT_STATE["reset_epoch"] = reset_epoch
    with _USAGE_LOCK:
        _USAGE_CACHE["fetched_at"] = 0.0


def reset_codex_usage_limit_state_for_tests() -> None:
    with _LIMIT_LOCK:
        _LIMIT_STATE["hit_at"] = 0.0
        _LIMIT_STATE["detail"] = ""
        _LIMIT_STATE["reset_epoch"] = None


def _active_limit_state() -> dict[str, Any] | None:
    with _LIMIT_LOCK:
        hit_at = float(_LIMIT_STATE.get("hit_at") or 0.0)
        if not hit_at:
            return None
        reset_epoch = _LIMIT_STATE.get("reset_epoch")
        now = time.time()
        if reset_epoch is not None and now >= float(reset_epoch):
            return None
        if reset_epoch is None and (now - hit_at) >= _LIMIT_WINDOW_SECONDS:
            return None
        return dict(_LIMIT_STATE)


def _reset_hint(limit_state: dict[str, Any] | None) -> str | None:
    if not limit_state:
        return None
    reset_epoch = limit_state.get("reset_epoch")
    if reset_epoch:
        reset_at = datetime.fromtimestamp(float(reset_epoch), tz=timezone.utc)
        return f"Resets around {reset_at.strftime('%H:%M UTC')}."
    hit_at = datetime.fromtimestamp(float(limit_state.get("hit_at") or 0.0), tz=timezone.utc)
    reset_guess = hit_at + timedelta(seconds=_LIMIT_WINDOW_SECONDS)
    return (
        f"Hit at {hit_at.strftime('%H:%M UTC')} — no public Codex quota API is available; "
        f"retry after the reported reset window or around {reset_guess.strftime('%H:%M UTC')}."
    )


def codex_usage_allows_agent_retry(usage: StatusRecord | None) -> bool:
    if not isinstance(usage, dict):
        return True
    return not bool(usage.get("limit_reached"))


def probe_codex_usage(*, force_refresh: bool = False) -> StatusRecord:
    cached = _USAGE_CACHE.get("payload")
    fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
    if (
        not force_refresh
        and cached is not None
        and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
    ):
        return dict(cached)

    with _USAGE_LOCK:
        cached = _USAGE_CACHE.get("payload")
        fetched_at = float(_USAGE_CACHE.get("fetched_at") or 0.0)
        if (
            not force_refresh
            and cached is not None
            and (time.monotonic() - fetched_at) < _USAGE_CACHE_TTL_SECONDS
        ):
            return dict(cached)

        totals = _read_local_log_totals()
        limit_state = _active_limit_state()
        reset_hint = _reset_hint(limit_state)
        if totals is None:
            payload: StatusRecord = {
                "ok": False,
                "source": "unavailable",
                "updated_at": _utc_now_iso(),
                "total_events": None,
                "events_24h": None,
                "estimated_bytes_24h": None,
                "turn_events": None,
                "latest_log_at": None,
                "limit_reached": limit_state is not None,
                "limit_reset_hint": reset_hint,
                "message": "Codex local usage telemetry unavailable on this host.",
                "display_message": None,
                "allows_agent_retry": limit_state is None,
            }
        else:
            payload = {
                "ok": True,
                "source": "codex_local_logs",
                "updated_at": _utc_now_iso(),
                **totals,
                "limit_reached": limit_state is not None,
                "limit_reset_hint": reset_hint,
                "message": (
                    "Local Codex CLI activity telemetry only; no live account-quota "
                    "percentage is exposed by the CLI."
                ),
                "display_message": (
                    f"{totals['events_24h']} local log events in 24h · "
                    f"{totals['estimated_bytes_24h']} estimated bytes"
                ),
                "allows_agent_retry": limit_state is None,
            }
        _USAGE_CACHE["fetched_at"] = time.monotonic()
        _USAGE_CACHE["payload"] = dict(payload)
        return dict(payload)


__all__ = [
    "codex_usage_allows_agent_retry",
    "probe_codex_usage",
    "record_codex_usage_limit_hit",
    "reset_codex_usage_limit_state_for_tests",
]
