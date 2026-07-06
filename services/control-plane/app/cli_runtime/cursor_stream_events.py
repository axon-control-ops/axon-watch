"""Parse Cursor CLI stream-json events into Cursor-style transcript blocks.

The assembled reply uses fenced block markers the console renders specially:

    :::thinking
    ...reasoning text...
    :::

    :::edit path/to/file.md +3 -1
    ...unified diff...
    :::

    :::tool Read README.md
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Callable


def parse_stream_event(line: str) -> dict[str, Any] | None:
    stripped = line.strip()
    if not stripped or not stripped.startswith("{"):
        return None
    try:
        event = json.loads(stripped)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


def assistant_text_from_event(event: dict[str, Any]) -> str:
    if event.get("type") != "assistant":
        return ""
    message = event.get("message")
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
    return "".join(parts)


def result_from_event(event: dict[str, Any]) -> tuple[str, bool] | None:
    """Return (result_text, is_error) for a terminal result event, else None."""
    if event.get("type") != "result":
        return None
    is_error = bool(event.get("is_error")) or str(event.get("subtype") or "") == "error"
    return str(event.get("result") or ""), is_error


def _relative_path(path: str, workspace_root: str) -> str:
    path = path.strip()
    if not path:
        return path

    root = Path(workspace_root).expanduser().resolve() if workspace_root else None
    candidate = Path(path).expanduser()
    if not candidate.is_absolute():
        return path.lstrip("./")

    try:
        resolved = candidate.resolve()
    except OSError:
        resolved = candidate

    if root is not None:
        try:
            return resolved.relative_to(root).as_posix()
        except ValueError:
            pass
        basename = resolved.name
        if basename and (root / basename).is_file():
            return basename

    parts = resolved.as_posix().split("/")
    if "README.md" in parts:
        return "README.md"
    return resolved.name or path


def _tool_block_from_event(event: dict[str, Any], workspace_root: str) -> str:
    """Render a completed tool_call event as a transcript block, or ''."""
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""

    edit = tool_call.get("editToolCall")
    if isinstance(edit, dict):
        args = edit.get("args") if isinstance(edit.get("args"), dict) else {}
        success = (edit.get("result") or {}).get("success") if isinstance(edit.get("result"), dict) else None
        path = _relative_path(str((success or args).get("path") or ""), workspace_root)
        if not isinstance(success, dict):
            return f"\n:::tool Edit failed {path}\n"
        added = int(success.get("linesAdded") or 0)
        removed = int(success.get("linesRemoved") or 0)
        diff = str(success.get("diffString") or "").strip()
        return f"\n:::edit {path} +{added} -{removed}\n{diff}\n:::\n"

    read = tool_call.get("readToolCall")
    if isinstance(read, dict):
        args = read.get("args") if isinstance(read.get("args"), dict) else {}
        path = _relative_path(str(args.get("path") or ""), workspace_root)
        return f"\n:::tool Read {path}\n"

    for key, value in tool_call.items():
        if not key.endswith("ToolCall") or not isinstance(value, dict):
            continue
        label = key[: -len("ToolCall")].replace("_", " ").capitalize()
        args = value.get("args") if isinstance(value.get("args"), dict) else {}
        target = str(args.get("path") or args.get("command") or "").strip()
        target = _relative_path(target, workspace_root)
        suffix = f" {target}" if target else ""
        return f"\n:::tool {label}{suffix}\n"
    return ""


class CursorStreamAssembler:
    """Assemble stream-json events into a block-annotated transcript."""

    def __init__(
        self,
        *,
        workspace_root: str = "",
        on_delta: Callable[[str, str], None] | None = None,
    ) -> None:
        self._workspace_root = workspace_root
        self._on_delta = on_delta
        self._parts: list[str] = []
        self._thinking_open = False
        self._saw_assistant_text = False
        self.result_text = ""
        self.error_text = ""

    @property
    def content(self) -> str:
        return "".join(self._parts)

    def _append(self, text: str) -> None:
        if not text:
            return
        self._parts.append(text)
        if self._on_delta is not None:
            self._on_delta(self.content, text)

    def _close_thinking(self) -> None:
        if self._thinking_open:
            self._append("\n:::\n")
            self._thinking_open = False

    def feed_line(self, line: str) -> None:
        event = parse_stream_event(line)
        if event is None:
            return

        event_type = str(event.get("type") or "")
        if event_type == "thinking":
            if event.get("subtype") == "completed":
                self._close_thinking()
                return
            delta = str(event.get("text") or "")
            if delta:
                if not self._thinking_open:
                    self._append("\n:::thinking\n")
                    self._thinking_open = True
                self._append(delta)
            return

        if event_type == "assistant":
            self._close_thinking()
            text = assistant_text_from_event(event)
            if text:
                self._saw_assistant_text = True
                self._append(text)
            return

        if event_type == "tool_call":
            self._close_thinking()
            self._append(_tool_block_from_event(event, self._workspace_root))
            return

        result = result_from_event(event)
        if result is not None:
            self._close_thinking()
            self.result_text, is_error = result
            if is_error:
                self.error_text = self.result_text or "Cursor CLI reported an error result."

    def finalize(self) -> str:
        self._close_thinking()
        content = self.content.strip()
        if not self._saw_assistant_text and self.result_text and not content:
            return self.result_text.strip()
        return content
