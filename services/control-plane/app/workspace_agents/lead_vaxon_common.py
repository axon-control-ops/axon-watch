"""Shared helpers for Lead → VAXON operator-thread posts."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.persistence import chat_store


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def new_message_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def get_or_create_operator_thread(workspace_id: str, *, created_at: str) -> dict:
    thread = chat_store.get_latest_thread_for_workspace(
        workspace_id,
        thread_kind="operator",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=None,
            created_at=created_at,
            thread_kind="operator",
            title="VAXON",
        )
    return thread


def broadcast_material_change_safe(receipt_id: str) -> None:
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=receipt_id)
    except Exception:
        pass


__all__ = [
    "broadcast_material_change_safe",
    "get_or_create_operator_thread",
    "new_message_id",
    "utc_now_iso",
]
