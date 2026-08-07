"""Thread retrieval and presentation helpers for chat conversations."""

from __future__ import annotations

from datetime import datetime, timezone

from app.cli_runtime.approval_gate import (
    agent_tool_execution_enabled,
    rewritten_execution_access_notice,
)
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


# Continuous-worker leads can accumulate thousands of messages / tens of MB per
# thread over weeks of shifts. Serving that unbounded to the browser forces it to
# JSON-parse and reactively render the whole history on every open, pegging the
# renderer's main thread for minutes (observed: 100%+ CPU, "Page Unresponsive").
# Cap what the UI gets by default; pass limit<=0 to opt into the full history.
#
# DashPro Lead (Dana) measured 2026-08-06: 4629 msgs total; a 300-msg window was
# still ~1.4MB with a single 550KB agent turn and 137 :::terminal fences — enough
# to freeze Chromium when Vue mounted every card. Keep the default window small
# and hard-cap per-message body size for the history payload.
DEFAULT_THREAD_HISTORY_LIMIT = 80
MAX_HISTORY_MESSAGE_CHARS = 64_000


def _cap_history_message_content(content: str) -> str:
    text = str(content or "")
    if len(text) <= MAX_HISTORY_MESSAGE_CHARS:
        return text
    head = 40_000
    tail = 20_000
    omitted = len(text) - head - tail
    return (
        f"{text[:head].rstrip()}\n\n"
        f"… [{omitted:,} characters omitted to keep the console responsive] …\n\n"
        f"{text[-tail:].lstrip()}"
    )


def get_chat_thread_history(
    thread_id: str,
    *,
    limit: int | None = DEFAULT_THREAD_HISTORY_LIMIT,
) -> dict[str, object]:
    from app.cli_runtime.research_stream_blocks import normalize_transcript_content

    thread = get_chat_thread(thread_id)
    items = chat_store.list_thread_messages(thread_id)
    total_count = len(items)
    if limit is not None and limit > 0 and total_count > limit:
        items = items[-limit:]
    normalized_items: list[dict[str, object]] = []
    for item in items:
        record = dict(item)
        content = str(record.get("content") or "")
        if record.get("role") == "agent" and content.strip():
            content = normalize_transcript_content(content)
        if content:
            record["content"] = _cap_history_message_content(content)
        normalized_items.append(record)
    enriched_items = _enrich_message_records(normalized_items)
    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "items": enriched_items,
        "count": len(enriched_items),
        "total_count": total_count,
    }


def sync_thread_execution_access_notices(thread_id: str, execution_access: str) -> int:
    """Rewrite stored consultative/Full-Access notices in this thread to match the
    operator's current Full Access toggle.

    Deliberately retroactive: the operator asked for old notices to track the live
    toggle rather than staying frozen at whatever was true when they were written.
    Only the fixed notice sentence is swapped (see ``rewritten_execution_access_notice``)
    — nothing else about the historical turn is touched. Returns the number of
    messages rewritten.
    """
    get_chat_thread(thread_id)  # raises ChatThreadNotFoundError if missing
    wants_full = agent_tool_execution_enabled(execution_access)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    updated = 0
    for item in chat_store.list_thread_messages(thread_id):
        content = str(item.get("content") or "")
        new_content = rewritten_execution_access_notice(content, wants_full=wants_full)
        if new_content is None:
            continue
        chat_store.update_message_content(
            message_id=str(item["message_id"]),
            content=new_content,
            updated_at=now,
        )
        updated += 1
    return updated


def _thread_preview_label(thread: dict[str, object]) -> str:
    title = str(thread.get("title") or "").strip()
    if title:
        return title
    return chat_store.first_operator_message_preview(str(thread["thread_id"]))


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
            "preview_label": _thread_preview_label(thread),
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
    title: str | None = None,
    employee_id: str | None = None,
    employee_role: str | None = None,
) -> dict[str, object]:
    get_workspace_record(workspace_id)
    kind = _normalize_thread_kind(thread_kind)
    cleaned_employee = str(employee_id or "").strip()
    if cleaned_employee:
        existing = chat_store.find_thread_for_employee(
            workspace_id,
            employee_id=cleaned_employee,
            thread_kind=kind,
        )
        if existing is not None:
            return {
                **existing,
                "preview_label": _thread_preview_label(existing),
            }
    created = chat_store.create_thread(
        workspace_id=workspace_id,
        run_id=run_id,
        created_at=_utc_now(),
        thread_kind=kind,
        title=title,
        employee_id=employee_id,
        employee_role=employee_role,
    )
    return {
        **created,
        "preview_label": _thread_preview_label(created) if created.get("title") else "New chat",
    }


def open_or_create_employee_chat_thread(
    workspace_id: str,
    *,
    employee_id: str,
    employee_role: str | None = None,
    title: str | None = None,
    thread_kind: str = "ide",
) -> dict[str, object]:
    """Find an existing IDE thread for this employee, or create a titled one."""
    return create_workspace_chat_thread(
        workspace_id,
        thread_kind=thread_kind,
        title=title,
        employee_id=employee_id,
        employee_role=employee_role,
    )


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
