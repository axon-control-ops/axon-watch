"""Chat/composer orchestration for the control-plane thin slice."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.chat.dispatch import build_command_dispatch_ack, resolve_command_dispatch
from app.persistence import chat_store
from app.workspace_catalog import WorkspaceNotFoundError, get_workspace_record


class ChatValidationError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _new_message_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def _validate_workspace(workspace_id: str) -> None:
    try:
        get_workspace_record(workspace_id)
    except WorkspaceNotFoundError as exc:
        raise ChatValidationError(str(exc)) from exc


def post_chat_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str | None = None,
    run_id: str | None = None,
) -> dict[str, object]:
    trimmed = content.strip()
    if not trimmed:
        raise ChatValidationError("content must not be empty")

    _validate_workspace(workspace_id)
    created_at = _utc_now()
    dispatch_run_id, run_record, dispatched = resolve_command_dispatch(
        workspace_id=workspace_id,
        content=trimmed,
        run_id=run_id,
    )
    ack_content = build_command_dispatch_ack(
        run_id=dispatch_run_id,
        phase=str(run_record["phase"]),
        dispatched=dispatched,
    )

    if thread_id:
        thread = chat_store.get_thread(thread_id)
        if thread is None:
            raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")
        if thread["workspace_id"] != workspace_id:
            raise ChatValidationError("thread_id does not belong to workspace_id")
    else:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=dispatch_run_id,
            created_at=created_at,
        )
        thread_id = thread["thread_id"]

    operator_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_operator"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id,
            "role": "operator",
            "content": trimmed,
            "created_at": created_at,
        }
    )
    system_message = chat_store.save_message(
        {
            "message_id": _new_message_id("message_system"),
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": dispatch_run_id,
            "role": "system",
            "content": ack_content,
            "created_at": created_at,
        }
    )

    return {
        "thread_id": thread_id,
        "messages": [operator_message, system_message],
        "run_id": dispatch_run_id,
        "dispatched": dispatched,
        "run": run_record,
    }


def get_chat_thread(thread_id: str) -> dict[str, object]:
    thread = chat_store.get_thread(thread_id)
    if thread is None:
        raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")
    return thread


def get_chat_thread_history(thread_id: str) -> dict[str, object]:
    thread = chat_store.get_thread(thread_id)
    if thread is None:
        raise chat_store.ChatThreadNotFoundError(f"thread not found: {thread_id}")

    items = chat_store.list_thread_messages(thread_id)
    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "items": items,
        "count": len(items),
    }


def get_workspace_chat_thread(workspace_id: str) -> dict[str, object]:
    get_workspace_record(workspace_id)
    thread = chat_store.get_latest_thread_for_workspace(workspace_id)
    if thread is None:
        return {
            "thread_id": None,
            "workspace_id": workspace_id,
            "run_id": None,
            "updated_at": None,
        }

    return {
        "thread_id": thread["thread_id"],
        "workspace_id": thread["workspace_id"],
        "run_id": thread["run_id"],
        "updated_at": thread["updated_at"],
    }
