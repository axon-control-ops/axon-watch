"""Extract generated image paths from Cursor stream-json tool events."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg"})
_MARKDOWN_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
_GENERATE_IMAGE_TOOL_HINT = re.compile(r"generate.*image|image.*generat", re.I)


def _is_image_path(value: str) -> bool:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned.startswith("http://") or cleaned.startswith("https://"):
        return False
    return Path(cleaned).suffix.lower() in _IMAGE_EXTENSIONS


def _collect_image_paths_from_value(value: Any, found: list[str]) -> None:
    if isinstance(value, str):
        if _is_image_path(value):
            found.append(value.strip())
        return
    if isinstance(value, dict):
        for item in value.values():
            _collect_image_paths_from_value(item, found)
        return
    if isinstance(value, list):
        for item in value:
            _collect_image_paths_from_value(item, found)


def _is_generate_image_tool_call(tool_call: dict[str, Any]) -> bool:
    for key in tool_call:
        if not isinstance(key, str) or not key.endswith("ToolCall"):
            continue
        if _GENERATE_IMAGE_TOOL_HINT.search(key):
            return True
        call = tool_call.get(key)
        if not isinstance(call, dict):
            continue
        args = call.get("args")
        if not isinstance(args, dict):
            continue
        for arg_key in ("tool", "toolName", "name"):
            label = str(args.get(arg_key) or "").strip()
            if label and _GENERATE_IMAGE_TOOL_HINT.search(label):
                return True
    return False


def dedupe_image_paths(paths: list[str]) -> list[str]:
    ranked = sorted(
        (str(raw or "").strip() for raw in paths),
        key=lambda item: (-len(item), item),
    )
    seen_full: set[str] = set()
    seen_names: set[str] = set()
    ordered: list[str] = []
    for cleaned in ranked:
        if not cleaned:
            continue
        key = cleaned.replace("\\", "/")
        basename = Path(cleaned).name
        if key in seen_full:
            continue
        if basename and basename in seen_names:
            continue
        seen_full.add(key)
        if basename:
            seen_names.add(basename)
        ordered.append(cleaned)
    return ordered


def image_paths_from_tool_call_event(event: dict[str, Any]) -> list[str]:
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return []
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict) or not _is_generate_image_tool_call(tool_call):
        return []

    found: list[str] = []
    for call in tool_call.values():
        if isinstance(call, dict):
            _collect_image_paths_from_value(call.get("result"), found)
            args = call.get("args")
            if isinstance(args, dict):
                for key in ("filename", "path", "filePath", "outputPath"):
                    value = str(args.get(key) or "").strip()
                    if _is_image_path(value):
                        found.append(value)
    return dedupe_image_paths(found)


def image_paths_from_markdown(content: str) -> list[str]:
    found: list[str] = []
    for match in _MARKDOWN_IMAGE_RE.finditer(str(content or "")):
        candidate = str(match.group(1) or "").strip().strip("\"'")
        if _is_image_path(candidate):
            found.append(candidate)
    return dedupe_image_paths(found)
