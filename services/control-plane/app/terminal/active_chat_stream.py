"""In-memory registry of the active Lane B / worker chat stream target per workspace."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from threading import Lock


@dataclass(frozen=True)
class ActiveChatStreamTarget:
    workspace_id: str
    thread_id: str
    message_id: str
    run_id: str = ""


_lock = Lock()
_targets: dict[str, ActiveChatStreamTarget] = {}


def register_active_chat_stream(
    *,
    workspace_id: str,
    thread_id: str,
    message_id: str,
    run_id: str = "",
) -> ActiveChatStreamTarget:
    clean_workspace = str(workspace_id or "").strip()
    clean_thread = str(thread_id or "").strip()
    clean_message = str(message_id or "").strip()
    if not clean_workspace or not clean_thread or not clean_message:
        raise ValueError("workspace_id, thread_id, and message_id are required")
    target = ActiveChatStreamTarget(
        workspace_id=clean_workspace,
        thread_id=clean_thread,
        message_id=clean_message,
        run_id=str(run_id or "").strip(),
    )
    with _lock:
        _targets[clean_workspace] = target
    return target


def clear_active_chat_stream(
    workspace_id: str = "",
    *,
    message_id: str | None = None,
) -> None:
    clean_workspace = str(workspace_id or "").strip()
    clean_message = str(message_id or "").strip() if message_id is not None else ""
    with _lock:
        if clean_workspace:
            current = _targets.get(clean_workspace)
            if current is None:
                return
            if clean_message and current.message_id != clean_message:
                return
            _targets.pop(clean_workspace, None)
            return
        if not clean_message:
            return
        for key, current in list(_targets.items()):
            if current.message_id == clean_message:
                _targets.pop(key, None)


def get_active_chat_stream(workspace_id: str) -> ActiveChatStreamTarget | None:
    clean = str(workspace_id or "").strip()
    if not clean:
        return None
    with _lock:
        target = _targets.get(clean)
        return deepcopy(target) if target is not None else None


def reset_active_chat_streams() -> None:
    with _lock:
        _targets.clear()


__all__ = [
    "ActiveChatStreamTarget",
    "register_active_chat_stream",
    "clear_active_chat_stream",
    "get_active_chat_stream",
    "reset_active_chat_streams",
]
