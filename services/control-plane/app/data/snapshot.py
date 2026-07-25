"""Read-only operator data snapshot for control-plane persistence tables."""

from __future__ import annotations

from typing import Any

from app.data.watch_adapter import fetch_watch_data_snapshot
from app.persistence import chat_store, handoff_store, run_store
from app.runs.queries import is_background_employee_run

_RUN_SUMMARY_FIELDS = (
    "run_id",
    "workspace_id",
    "lane_id",
    "mode",
    "status",
    "phase",
    "summary",
    "started_at",
    "updated_at",
    "ended_at",
)


def _utc_now_iso() -> str:
    from datetime import datetime, timezone

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _truncate_text(value: str, *, max_len: int = 160) -> str:
    text = value.strip()
    if len(text) <= max_len:
        return text
    return f"{text[: max_len - 1]}…"


def _summarize_run(record: dict[str, Any]) -> dict[str, Any]:
    return {field: record.get(field, "") for field in _RUN_SUMMARY_FIELDS}


def _summarize_message(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": record.get("message_id", ""),
        "thread_id": record.get("thread_id", ""),
        "workspace_id": record.get("workspace_id", ""),
        "run_id": record.get("run_id", ""),
        "role": record.get("role", ""),
        "content_preview": _truncate_text(str(record.get("content", ""))),
        "created_at": record.get("created_at", ""),
    }


def _control_plane_tables(*, limit: int) -> dict[str, object]:
    max_limit = max(1, min(100, int(limit or 50)))
    all_runs = [
        record
        for record in run_store.list_runs()
        if not is_background_employee_run(record)
    ]
    recent_runs = list(reversed(all_runs))[:max_limit]
    run_items = [_summarize_run(record) for record in recent_runs]
    thread_items = chat_store.list_threads(limit=max_limit)
    message_items = [_summarize_message(record) for record in chat_store.list_recent_messages(limit=max_limit)]
    handoff_items = handoff_store.list_recent_handoffs(limit=max_limit)

    return {
        "runs": {
            "total": len(all_runs),
            "count": len(run_items),
            "items": run_items,
        },
        "chat_threads": {
            "total": chat_store.count_threads(),
            "count": len(thread_items),
            "items": thread_items,
        },
        "chat_messages": {
            "total": chat_store.count_messages(),
            "count": len(message_items),
            "items": message_items,
        },
        "handoffs": {
            "total": handoff_store.count_handoffs(),
            "count": len(handoff_items),
            "items": handoff_items,
        },
    }


def operator_data_snapshot(*, limit: int = 50) -> dict[str, object]:
    watch_tables = fetch_watch_data_snapshot(limit=limit).get("tables", {})
    if not isinstance(watch_tables, dict):
        watch_tables = {}

    return {
        "updated_at": _utc_now_iso(),
        "control_plane": _control_plane_tables(limit=limit),
        "watch": watch_tables,
    }
