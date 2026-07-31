"""Merge live Axon agent-terminal job fences into chat transcript content."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from app.cli_runtime.stream_blocks.terminal_blocks import (
    render_axon_job_terminal_fence,
    upsert_axon_job_terminal_fence,
)

_lock = Lock()
_fences: dict[str, dict[str, "LiveJobFence"]] = {}


@dataclass
class LiveJobFence:
    job_id: str
    message_id: str
    command: str
    body: str = ""
    closed: bool = False
    exit_code: int | None = None
    meta: dict[str, Any] = field(default_factory=dict)


def register_live_job_fence(
    *,
    job_id: str,
    message_id: str,
    command: str,
) -> LiveJobFence:
    clean_job = str(job_id or "").strip()
    clean_message = str(message_id or "").strip()
    fence = LiveJobFence(
        job_id=clean_job,
        message_id=clean_message,
        command=str(command or "").strip(),
    )
    with _lock:
        by_message = _fences.setdefault(clean_message, {})
        by_message[clean_job] = fence
    return deepcopy(fence)


def append_live_job_fence_body(job_id: str, message_id: str, chunk: str) -> LiveJobFence | None:
    clean_job = str(job_id or "").strip()
    clean_message = str(message_id or "").strip()
    text = str(chunk or "")
    if not clean_job or not clean_message or not text:
        return None
    with _lock:
        fence = _fences.get(clean_message, {}).get(clean_job)
        if fence is None or fence.closed:
            return None
        fence.body += text
        return deepcopy(fence)


def close_live_job_fence(
    job_id: str,
    message_id: str,
    *,
    exit_code: int | None = None,
) -> LiveJobFence | None:
    clean_job = str(job_id or "").strip()
    clean_message = str(message_id or "").strip()
    with _lock:
        fence = _fences.get(clean_message, {}).get(clean_job)
        if fence is None:
            return None
        fence.closed = True
        if exit_code is not None:
            fence.exit_code = int(exit_code)
        return deepcopy(fence)


def drop_live_job_fence(job_id: str, message_id: str) -> None:
    clean_job = str(job_id or "").strip()
    clean_message = str(message_id or "").strip()
    with _lock:
        by_message = _fences.get(clean_message)
        if not by_message:
            return
        by_message.pop(clean_job, None)
        if not by_message:
            _fences.pop(clean_message, None)


def list_live_job_fences(message_id: str) -> list[LiveJobFence]:
    clean_message = str(message_id or "").strip()
    with _lock:
        return [deepcopy(item) for item in _fences.get(clean_message, {}).values()]


def merge_active_agent_job_terminals(message_id: str, content: str) -> str:
    """Ensure live/closed Axon job fences for ``message_id`` are present in content."""
    fences = list_live_job_fences(message_id)
    if not fences:
        return content
    merged = str(content or "")
    for fence in fences:
        rendered = render_axon_job_terminal_fence(
            command=fence.command,
            job_id=fence.job_id,
            body=fence.body,
            closed=fence.closed,
            exit_code=fence.exit_code,
        )
        merged = upsert_axon_job_terminal_fence(merged, rendered, job_id=fence.job_id)
    return merged


def reset_live_job_fences() -> None:
    with _lock:
        _fences.clear()


__all__ = [
    "LiveJobFence",
    "register_live_job_fence",
    "append_live_job_fence_body",
    "close_live_job_fence",
    "drop_live_job_fence",
    "list_live_job_fences",
    "merge_active_agent_job_terminals",
    "reset_live_job_fences",
]
