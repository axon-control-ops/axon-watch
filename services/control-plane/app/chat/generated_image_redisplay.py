"""Fast-path redisplay of generated images already present in a chat thread."""

from __future__ import annotations

import re
from typing import Any

from app.chat.open_file_intent import image_paths_from_thread
from app.chat.lane_b_image_attachments import resolve_generated_image_path
from app.persistence import chat_store
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_REDISPLAY_REQUEST_RE = re.compile(
    r"\b(?:"
    r"show(?:\s+me)?(?:\s+(?:the|those|these|my|generated)){0,2}\s+images?"
    r"|display(?:\s+(?:the|those|these|my|generated)){0,2}\s+images?"
    r"|let\s+me\s+see(?:\s+(?:the|those|these|my|generated)){0,2}\s+images?"
    r"|open(?:\s+(?:the|those|these|my|generated)){0,2}\s+images?"
    r"|view(?:\s+(?:the|those|these|my|generated)){0,2}\s+images?"
    r"|where(?:\s+are|'?re)\s+(?:(?:the|those|these|my|generated)\s+){0,2}images?"
    r")\b",
    re.IGNORECASE,
)
_GENERATION_REQUEST_RE = re.compile(
    r"\b(?:generate|create|make|draw|render)\b.{0,40}\b(?:image|mockup|logo|illustration)\b",
    re.IGNORECASE,
)
_OF_SUBJECT_RE = re.compile(r"\b(?:of|for|with|showing|depicting)\b", re.IGNORECASE)


def looks_like_generated_image_redisplay_request(message: str) -> bool:
    text = str(message or "").strip()
    if not text:
        return False
    if _GENERATION_REQUEST_RE.search(text) and _OF_SUBJECT_RE.search(text):
        return False
    if _GENERATION_REQUEST_RE.search(text) and not _REDISPLAY_REQUEST_RE.search(text):
        return False
    return bool(_REDISPLAY_REQUEST_RE.search(text))


def collect_thread_generated_image_paths(
    thread_id: str,
    *,
    workspace_id: str,
    max_paths: int = 6,
) -> list[str]:
    raw_paths = image_paths_from_thread(thread_id)
    if not raw_paths:
        return []

    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        workspace_root = None

    ordered: list[str] = []
    seen: set[str] = set()
    for raw_path in raw_paths:
        cleaned = str(raw_path or "").strip().replace("\\", "/")
        if not cleaned or cleaned in seen:
            continue
        resolved = resolve_generated_image_path(cleaned, workspace_root=workspace_root)
        if resolved is None and workspace_root is None:
            # Keep relative transcript paths even when workspace root is unavailable.
            display = cleaned
        elif resolved is None:
            continue
        else:
            if workspace_root is not None:
                try:
                    display = resolved.relative_to(workspace_root).as_posix()
                except ValueError:
                    display = cleaned
            else:
                display = cleaned
        if display in seen:
            continue
        seen.add(display)
        ordered.append(display)
        if len(ordered) >= max_paths:
            break
    return ordered


def build_generated_image_redisplay_reply(paths: list[str]) -> str:
    cleaned = [str(path).strip() for path in paths if str(path).strip()]
    if not cleaned:
        return ""
    intro = (
        "Here are the generated images from this thread:"
        if len(cleaned) > 1
        else "Here is the generated image from this thread:"
    )
    blocks = "\n\n".join(f":::image {path}" for path in cleaned)
    return f"{intro}\n\n{blocks}"


def maybe_generated_image_redisplay_reply(
    user_message: str,
    *,
    workspace_id: str,
    thread_id: str | None,
) -> str | None:
    if not thread_id or not looks_like_generated_image_redisplay_request(user_message):
        return None
    if chat_store.get_thread(thread_id) is None:
        return None
    paths = collect_thread_generated_image_paths(thread_id, workspace_id=workspace_id)
    if not paths:
        return None
    reply = build_generated_image_redisplay_reply(paths)
    return reply or None


__all__ = [
    "build_generated_image_redisplay_reply",
    "collect_thread_generated_image_paths",
    "looks_like_generated_image_redisplay_request",
    "maybe_generated_image_redisplay_reply",
]
