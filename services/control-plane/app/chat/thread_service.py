"""Thread retrieval and presentation helpers for chat conversations."""

from __future__ import annotations

from datetime import datetime, timezone

from app.persistence import attachment_store, chat_store
from app.workspace_catalog import get_workspace_record


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_thread_kind(thread_kind: str | None) -> str:
    kind = str(thread_kind or "operator").strip().lower() or "operator"
    return kind if kind in {"operator", "ide"} else "operator"


def _enrich_message_records(records: list[dict[str, object]]) -> list[dict[str, object]]:
    message_ids = [str(item.get("message_id") or "") for item in records]
    grouped = attachment_store.list_attachments_for_messages(message_ids)
    enriched: list[dict[str, object]] = []
    for record in records:
        next_record = dict(record)
        message_id = str(record.get("message_id") or "")
        attachments = grouped.get(message_id, [])
        if attachments:
            next_record["attachments"] = [
                attachment_store.serialize_attachment(item) for item in attachments
            ]
        enriched.append(next_record)
    return enriched


def get_chat_thread(thread_id: str) -> dict[str, object]:
    thread = chat_store.get_thread(thread_id)
    if thread is None:
        raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")
    return thread


def get_chat_thread_history(thread_id: str) -> dict[str, object]:
    from app.cli_runtime.research_stream_blocks import normalize_transcript_content

    thread = get_chat_thread(thread_id)
    items = chat_store.list_thread_messages(thread_id)
    normalized_items: list[dict[str, object]] = []
    for item in items:
        record = dict(item)
        if record.get("role") == "agent":
            content = str(record.get("content") or "")
            if content.strip():
                record["content"] = normalize_transcript_content(content)
        normalized_items.append(record)
    enriched_items = _enrich_message_records(normalized_items)
    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "items": enriched_items,
        "count": len(enriched_items),
    }


def list_workspace_chat_threads(
    workspace_id: str,
    *,
    thread_kind: str = "ide",
    limit: int = 25,
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    threads = chat_store.list_threads_for_workspace(
        workspace_id,
        thread_kind=kind,
        limit=limit,
    )
    items = [
        {
            **thread,
            "preview_label": chat_store.first_operator_message_preview(str(thread["thread_id"])),
        }
        for thread in threads
    ]
    return {
        "workspace_id": workspace_id,
        "thread_kind": kind,
        "items": items,
        "count": len(items),
    }


def create_workspace_chat_thread(
    workspace_id: str,
    *,
    thread_kind: str = "ide",
    run_id: str | None = None,
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    created = chat_store.create_thread(
        workspace_id=workspace_id,
        run_id=run_id,
        created_at=_utc_now(),
        thread_kind=kind,
    )
    return {
        **created,
        "preview_label": "New chat",
    }


def get_workspace_chat_thread(
    workspace_id: str,
    *,
    thread_kind: str = "operator",
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    thread = chat_store.get_latest_thread_for_workspace(workspace_id, thread_kind=kind)
    if thread is None:
        return {
            "thread_id": None,
            "workspace_id": workspace_id,
            "run_id": None,
            "thread_kind": kind,
            "updated_at": None,
        }
    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "thread_kind": thread.get("thread_kind", kind),
        "updated_at": thread["updated_at"],
    }
