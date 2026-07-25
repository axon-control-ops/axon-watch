"""Resolve operator prompts that request opening a workspace file or generated image."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from app.cli_runtime.generated_image_paths import image_paths_from_markdown
from app.chat.lane_b_image_attachments import resolve_generated_image_path
from app.persistence import chat_store
from app.terminal.workspace_roots import WorkspaceRootError, resolve_workspace_root

_IMAGE_HEADER_RE = re.compile(r"^:::image\s+(.+)$")
_OPEN_IMAGE_RE = re.compile(
    r"^\s*(?:please\s+)?(?:can you\s+)?(?:open|show|surface|display|view)\s+"
    r"(?:the\s+)?(?:(?:generated|recent|latest)\s+)?(?:image|mockup|picture|png|mockup image)\b",
    re.IGNORECASE,
)
_OPEN_PATH_RE = re.compile(
    r"^\s*(?:please\s+)?(?:can you\s+)?(?:open|show|surface|display|view)\s+"
    r"(?:the\s+)?(?:file\s+)?[`'\"]?([^\s`'\"]+\.(?:png|jpg|jpeg|gif|webp|bmp|svg))[`'\"]?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class OpenFileIntent:
    open_file_path: str


def _looks_like_open_image(content: str) -> bool:
    text = content.strip()
    if not text:
        return False
    if _OPEN_IMAGE_RE.search(text):
        return True
    return bool(_OPEN_PATH_RE.match(text))


def _image_paths_from_message_content(content: str) -> list[str]:
    paths: list[str] = []
    for line in str(content or "").splitlines():
        match = _IMAGE_HEADER_RE.match(line.strip())
        if match:
            candidate = str(match.group(1) or "").strip()
            if candidate:
                paths.append(candidate)
    paths.extend(image_paths_from_markdown(content))
    return paths


def _image_paths_from_thread(thread_id: str) -> list[str]:
    paths: list[str] = []
    for message in reversed(chat_store.list_thread_messages(thread_id)):
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        if role == "agent":
            paths.extend(_image_paths_from_message_content(content))
            for match in re.finditer(
                r"[`'\"]?((?:assets/)?[\w./-]+\.(?:png|jpg|jpeg|gif|webp))[`'\"]?",
                content,
                re.IGNORECASE,
            ):
                paths.append(str(match.group(1) or "").strip())
        attachments = message.get("attachments")
        if isinstance(attachments, list):
            for attachment in attachments:
                if not isinstance(attachment, dict):
                    continue
                filename = str(attachment.get("filename") or "").strip()
                if filename:
                    paths.append(filename)
    deduped: list[str] = []
    seen: set[str] = set()
    for raw_path in paths:
        cleaned = raw_path.strip().replace("\\", "/")
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        deduped.append(cleaned)
    return deduped


def _latest_assets_image(workspace_id: str) -> str | None:
    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        return None

    assets_dir = workspace_root / "assets"
    if not assets_dir.is_dir():
        return None

    candidates = [
        path
        for path in assets_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ]
    if not candidates:
        return None

    latest = max(candidates, key=lambda item: item.stat().st_mtime)
    try:
        return latest.relative_to(workspace_root).as_posix()
    except ValueError:
        return latest.name


def _resolve_open_file_path(
    *,
    workspace_id: str,
    operator_content: str,
    thread_id: str | None,
    lane_b_result: dict[str, object] | None = None,
    agent_content: str | None = None,
) -> str | None:
    explicit = _OPEN_PATH_RE.match(operator_content.strip())
    if explicit:
        candidate = str(explicit.group(1) or "").strip()
        if candidate:
            return candidate

    candidates: list[str] = []
    if lane_b_result:
        raw_paths = lane_b_result.get("generated_image_paths")
        if isinstance(raw_paths, list):
            candidates.extend(str(item).strip() for item in raw_paths if str(item).strip())
    if agent_content:
        candidates.extend(_image_paths_from_message_content(agent_content))
    if thread_id:
        candidates.extend(_image_paths_from_thread(thread_id))

    try:
        workspace_root = resolve_workspace_root(workspace_id)
    except WorkspaceRootError:
        workspace_root = None

    for raw_path in candidates:
        resolved = resolve_generated_image_path(raw_path, workspace_root=workspace_root)
        if resolved is not None:
            if workspace_root is not None:
                try:
                    return resolved.relative_to(workspace_root).as_posix()
                except ValueError:
                    pass
            return raw_path.replace("\\", "/")

    return _latest_assets_image(workspace_id)


def image_paths_from_thread(thread_id: str) -> list[str]:
    return _image_paths_from_thread(thread_id)


def resolve_open_file_intent(
    content: str,
    *,
    workspace_id: str,
    thread_id: str | None = None,
    lane_b_result: dict[str, object] | None = None,
    agent_content: str | None = None,
) -> OpenFileIntent | None:
    if not _looks_like_open_image(content):
        return None

    open_file_path = _resolve_open_file_path(
        workspace_id=workspace_id,
        operator_content=content,
        thread_id=thread_id,
        lane_b_result=lane_b_result,
        agent_content=agent_content,
    )
    if not open_file_path:
        return None
    return OpenFileIntent(open_file_path=open_file_path)


def open_file_ui_action(intent: OpenFileIntent, *, workspace_id: str) -> dict[str, object]:
    return {
        "type": "open_source",
        "workspace_id": workspace_id,
        "open_file_path": intent.open_file_path,
    }
