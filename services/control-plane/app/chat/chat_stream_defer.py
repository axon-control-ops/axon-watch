"""Defer chat_stream_done/close while Axon agent-terminal jobs still tee to chat.

Lane B / worker turns often finish right after enqueueing a long OTA job. Closing
the SSE at that moment drops mid-run ``persist_stream_delta`` events, so the
console never sees live Expo progress. Keep the stream open until open job
fences for the agent message settle.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock
from typing import Any

from app.chat.stream_hub import clear_chat_stream_buffer, close_chat_stream, publish_chat_stream_event
from app.terminal.agent_job_chat import list_live_job_fences

_lock = Lock()
_deferred: dict[str, "DeferredChatStreamClose"] = {}


@dataclass
class DeferredChatStreamClose:
    thread_id: str
    message_id: str
    terminal_payload: dict[str, Any]


def message_has_open_live_job_fences(message_id: str) -> bool:
    return any(not fence.closed for fence in list_live_job_fences(message_id))


def finish_chat_stream(
    *,
    thread_id: str,
    message_id: str,
    terminal_payload: dict[str, Any],
) -> bool:
    """Publish done/error and close the SSE, or defer until live job fences close.

    Returns True when the stream was closed immediately; False when deferred.
    """
    clean_thread = str(thread_id or "").strip()
    clean_message = str(message_id or "").strip()
    payload = dict(terminal_payload)
    if not clean_thread or not clean_message:
        if clean_thread:
            publish_chat_stream_event(clean_thread, payload)
            close_chat_stream(clean_thread)
            clear_chat_stream_buffer(clean_thread)
        return True

    if message_has_open_live_job_fences(clean_message):
        with _lock:
            _deferred[clean_message] = DeferredChatStreamClose(
                thread_id=clean_thread,
                message_id=clean_message,
                terminal_payload=payload,
            )
        publish_chat_stream_event(
            clean_thread,
            {
                "type": "chat_stream_milestone",
                "thread_id": clean_thread,
                "message_id": clean_message,
                "milestone": "axon_terminal_job_streaming",
                "detail": (
                    "Agent turn text is ready; Axon terminal job is still streaming "
                    "into the open :::terminal card."
                ),
                "content": str(payload.get("content") or ""),
            },
        )
        return False

    publish_chat_stream_event(clean_thread, payload)
    close_chat_stream(clean_thread)
    clear_chat_stream_buffer(clean_thread)
    return True


def release_deferred_chat_stream_if_idle(message_id: str) -> bool:
    """If a deferred close is waiting and no open fences remain, publish + close."""
    clean_message = str(message_id or "").strip()
    if not clean_message or message_has_open_live_job_fences(clean_message):
        return False
    with _lock:
        deferred = _deferred.pop(clean_message, None)
    if deferred is None:
        return False

    payload = dict(deferred.terminal_payload)
    try:
        from app.persistence import chat_store
        from app.terminal.agent_job_chat import merge_active_agent_job_terminals

        row = chat_store.get_message(clean_message)
        if row is not None:
            content = merge_active_agent_job_terminals(
                clean_message,
                str(row.get("content") or ""),
            )
            payload["content"] = content
    except Exception:  # noqa: BLE001 — still close the stream
        pass

    publish_chat_stream_event(deferred.thread_id, payload)
    close_chat_stream(deferred.thread_id)
    clear_chat_stream_buffer(deferred.thread_id)
    return True


def reset_deferred_chat_streams() -> None:
    with _lock:
        _deferred.clear()


def list_deferred_chat_streams() -> dict[str, DeferredChatStreamClose]:
    with _lock:
        return {key: deepcopy(value) for key, value in _deferred.items()}


__all__ = [
    "DeferredChatStreamClose",
    "message_has_open_live_job_fences",
    "finish_chat_stream",
    "release_deferred_chat_stream_if_idle",
    "reset_deferred_chat_streams",
    "list_deferred_chat_streams",
]
