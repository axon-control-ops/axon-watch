"""Lane B helpers for no-runtime chat fast paths."""

from __future__ import annotations

from collections.abc import Callable

from app.persistence import chat_store
from app.workspace_handoffs import create_workspace_handoff

ThreadResolver = Callable[..., tuple[dict[str, object], str]]
MessageIdFactory = Callable[[str], str]


def post_workspace_switch_message(
    *,
    source_workspace_id: str,
    target_workspace_id: str,
    display_name: str,
    content: str,
    thread_id: str | None,
    created_at: str,
    run_id: str | None,
    agent_content: str,
    ui_action: dict[str, object],
    resolve_thread: ThreadResolver,
    new_message_id: MessageIdFactory,
) -> dict[str, object]:
    if source_workspace_id != target_workspace_id:
        try:
            create_workspace_handoff(
                source_workspace_id=source_workspace_id,
                target_workspace_id=target_workspace_id,
                task=content.strip(),
                reason="Lane B workspace switch",
            )
        except Exception:
            pass

    thread, resolved_thread_id = resolve_thread(
        workspace_id=source_workspace_id,
        thread_id=thread_id,
        thread_kind="ide",
        run_id=run_id,
        created_at=created_at,
    )
    system_content = (
        f"Lane B — switched active workspace to {target_workspace_id} "
        f"({display_name})."
    )
    operator_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_operator"),
            "thread_id": resolved_thread_id,
            "workspace_id": source_workspace_id,
            "run_id": thread.get("run_id"),
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    system_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_system"),
            "thread_id": resolved_thread_id,
            "workspace_id": source_workspace_id,
            "run_id": thread.get("run_id"),
            "role": "system",
            "content": system_content,
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": resolved_thread_id,
            "workspace_id": source_workspace_id,
            "run_id": thread.get("run_id"),
            "role": "agent",
            "content": agent_content,
            "created_at": created_at,
        }
    )
    return {
        "thread_id": resolved_thread_id,
        "messages": [operator_message, system_message, agent_message],
        "run_id": thread.get("run_id") or "",
        "dispatched": False,
        "run": None,
        "streaming": False,
        "ui_action": ui_action,
    }


def post_image_redisplay_message(
    *,
    workspace_id: str,
    content: str,
    thread_id: str | None,
    run_id: str | None,
    created_at: str,
    redisplay_reply: str,
    resolve_thread: ThreadResolver,
    new_message_id: MessageIdFactory,
) -> dict[str, object]:
    thread, resolved_thread_id = resolve_thread(
        workspace_id=workspace_id,
        thread_id=thread_id,
        thread_kind="ide",
        run_id=run_id,
        created_at=created_at,
    )
    operator_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_operator"),
            "thread_id": resolved_thread_id,
            "workspace_id": workspace_id,
            "run_id": thread.get("run_id") or run_id or "",
            "role": "operator",
            "content": content,
            "created_at": created_at,
        }
    )
    agent_message = chat_store.save_message(
        {
            "message_id": new_message_id("message_agent"),
            "thread_id": resolved_thread_id,
            "workspace_id": workspace_id,
            "run_id": thread.get("run_id") or run_id or "",
            "role": "agent",
            "content": redisplay_reply,
            "created_at": created_at,
        }
    )
    return {
        "thread_id": resolved_thread_id,
        "messages": [operator_message, agent_message],
        "run_id": thread.get("run_id") or run_id or "",
        "dispatched": False,
        "run": None,
        "streaming": False,
        "image_redisplay": True,
    }


__all__ = ["post_image_redisplay_message", "post_workspace_switch_message"]
