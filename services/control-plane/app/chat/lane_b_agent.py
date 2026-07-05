"""Lane B free-form agent replies for IDE composer modes (ask / agent / plan)."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root
from app.workspace_files import WorkspaceFileError, list_workspace_files


@dataclass(frozen=True)
class LaneBContext:
    workspace_id: str
    composer_mode: str
    active_file_path: str | None = None


def _ollama_base_url() -> str:
    return os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")


def _ollama_model() -> str:
    return os.environ.get("AXON_WATCH_LANE_B_MODEL", "llama3.2").strip() or "llama3.2"


def _read_file_preview(workspace_id: str, path: str, *, max_chars: int = 1200) -> str:
    from app.workspace_files import read_workspace_file

    try:
        payload = read_workspace_file(workspace_id, path)
        content = str(payload.get("content", ""))
        if len(content) <= max_chars:
            return content
        return f"{content[: max_chars - 3].rstrip()}..."
    except (WorkspaceFileError, OSError):
        return ""


def build_lane_b_context_block(context: LaneBContext) -> str:
    lines = [
        f"Workspace: {context.workspace_id}",
        f"Composer mode: {context.composer_mode}",
    ]
    try:
        root = resolve_workspace_root(context.workspace_id)
        lines.append(f"Project root: {root}")
    except WorkspaceRootError as exc:
        lines.append(f"Project root unavailable: {exc}")

    if context.active_file_path:
        preview = _read_file_preview(context.workspace_id, context.active_file_path)
        lines.append(f"Active file: {context.active_file_path}")
        if preview:
            lines.append(f"Active file preview:\n{preview}")

    try:
        files = list_workspace_files(context.workspace_id)
        if files:
            sample = ", ".join(item["path"] for item in files[:12])
            lines.append(f"Workspace files (sample): {sample}")
    except (WorkspaceFileError, OSError):
        pass

    return "\n".join(lines)


def _system_prompt(context: LaneBContext) -> str:
    mode = context.composer_mode
    if mode == "ask":
        return (
            "You are Axon-X Lane B in read-only Ask mode. Answer using the supplied "
            "workspace context. Do not claim you edited files or ran shell commands."
        )
    if mode == "plan":
        return (
            "You are Axon-X Lane B in Plan mode. Produce a short numbered plan using "
            "the workspace context. Do not claim execution happened."
        )
    return (
        "You are Axon-X Lane B in Agent mode. Propose concrete next steps for the "
        "operator. You may suggest exact commands but do not claim you ran them."
    )


def _ollama_chat(*, system: str, context_block: str, user_prompt: str) -> str:
    url = f"{_ollama_base_url()}/api/chat"
    payload = {
        "model": _ollama_model(),
        "stream": False,
        "messages": [
            {"role": "system", "content": f"{system}\n\n{context_block}"},
            {"role": "user", "content": user_prompt},
        ],
    }
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))
    message = body.get("message")
    if isinstance(message, dict):
        content = str(message.get("content", "")).strip()
        if content:
            return content
    raise RuntimeError("ollama returned empty response")


def _fallback_reply(*, context: LaneBContext, user_prompt: str, reason: str) -> str:
    context_block = build_lane_b_context_block(context)
    return (
        f"Lane B ({context.composer_mode}) is active, but the local model bridge is "
        f"unavailable ({reason}).\n\n"
        f"Operator request:\n{user_prompt.strip()}\n\n"
        f"Workspace context:\n```\n{context_block}\n```\n\n"
        "To enable AI replies, start Ollama locally and set "
        "`OLLAMA_HOST` / `AXON_WATCH_LANE_B_MODEL`. Operator commands (`git status`, "
        "`run …`) still work in Command mode."
    )


def generate_lane_b_reply(*, context: LaneBContext, user_prompt: str) -> str:
    trimmed = user_prompt.strip()
    if not trimmed:
        return "Send a prompt to start Lane B conversation."

    system = _system_prompt(context)
    context_block = build_lane_b_context_block(context)
    try:
        return _ollama_chat(system=system, context_block=context_block, user_prompt=trimmed)
    except (URLError, TimeoutError, OSError, json.JSONDecodeError, RuntimeError) as exc:
        return _fallback_reply(context=context, user_prompt=trimmed, reason=str(exc))


def is_lane_b_composer_mode(composer_mode: str | None) -> bool:
    normalized = str(composer_mode or "command").strip().lower()
    return normalized in {"ask", "agent", "plan"}


def should_use_lane_b(*, composer_mode: str | None, command_intent: str) -> bool:
    return command_intent == "unsupported" and is_lane_b_composer_mode(composer_mode)
