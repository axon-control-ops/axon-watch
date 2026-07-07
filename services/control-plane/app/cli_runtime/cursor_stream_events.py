"""Parse Cursor CLI stream-json events into Cursor-style transcript blocks.

The assembled reply uses fenced block markers the console renders specially:

    :::thinking
    ...reasoning text...
    :::

    :::edit path/to/file.md +3 -1
    ...unified diff...
    :::

    :::tool Read README.md

    :::research vite configuration
    - Vite Guide | https://vitejs.dev/guide/
    Official Vite documentation.
    :::
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


_TERMINAL_OUTPUT_LIMIT = 4000
_RESEARCH_ITEM_LIMIT = 8


def _research_items_from_result(result: Any) -> list[dict[str, str]]:
    if not isinstance(result, dict):
        return []

    containers: list[dict[str, Any]] = []
    success = result.get("success")
    if isinstance(success, dict):
        containers.append(success)
    containers.append(result)

    raw_results: Any = None
    for container in containers:
        for key in ("results", "items", "sources", "citations", "matches"):
            candidate = container.get(key)
            if isinstance(candidate, list) and candidate:
                raw_results = candidate
                break
        if raw_results is not None:
            break

    if not isinstance(raw_results, list):
        return []

    items: list[dict[str, str]] = []
    for entry in raw_results:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title") or entry.get("name") or entry.get("label") or "").strip()
        url = str(entry.get("url") or entry.get("link") or entry.get("href") or "").strip()
        snippet = str(
            entry.get("snippet")
            or entry.get("summary")
            or entry.get("description")
            or entry.get("content")
            or ""
        ).strip()
        if not title and not url and not snippet:
            continue
        items.append(
            {
                "title": title or (url or "Source"),
                "url": url,
                "snippet": snippet,
            }
        )
        if len(items) >= _RESEARCH_ITEM_LIMIT:
            break
    return items


def _research_block(query: str, items: list[dict[str, str]]) -> str:
    trimmed_query = query.strip() or "Research"
    lines = [f"\n:::research {trimmed_query}"]
    for item in items:
        title = str(item.get("title") or "Source").strip()
        url = str(item.get("url") or "").strip()
        snippet = str(item.get("snippet") or "").strip()
        lines.append(f"- {title} | {url or 'about:blank'}")
        if snippet:
            lines.append(snippet)
    lines.append(":::\n")
    return "\n".join(lines)


def _research_block_from_tool_call(tool_call: dict[str, Any]) -> str:
    for key in ("webSearchToolCall", "webFetchToolCall", "searchToolCall", "fetchToolCall"):
        call = tool_call.get(key)
        if not isinstance(call, dict):
            continue
        args = call.get("args") if isinstance(call.get("args"), dict) else {}
        query = str(
            args.get("query")
            or args.get("search_term")
            or args.get("url")
            or args.get("prompt")
            or ""
        ).strip()
        items = _research_items_from_result(call.get("result"))
        if items or query:
            return _research_block(query or key.replace("ToolCall", ""), items)
    return ""


def _shell_output_from_result(result: Any) -> str:
    """Best-effort extraction of command output from a shell tool result."""
    if not isinstance(result, dict):
        return ""
    for container in (result.get("success"), result):
        if not isinstance(container, dict):
            continue
        parts: list[str] = []
        for key in ("stdout", "output", "stderr"):
            value = container.get(key)
            if isinstance(value, str) and value.strip():
                parts.append(value.rstrip())
        if parts:
            return "\n".join(parts)
    return ""


def _terminal_block(command: str, output: str) -> str:
    trimmed = output.strip()
    if len(trimmed) > _TERMINAL_OUTPUT_LIMIT:
        trimmed = f"{trimmed[:_TERMINAL_OUTPUT_LIMIT].rstrip()}\n… (output truncated)"
    body = f"\n{trimmed}\n" if trimmed else "\n"
    return f"\n:::terminal {command}{body}:::\n"


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

    research_block = _research_block_from_tool_call(tool_call)
    if research_block:
        return research_block

    # Shell commands render as a terminal block (command + captured output),
    # mirroring how Cursor surfaces agent-run commands in its own terminal.
    for shell_key in ("shellToolCall", "runTerminalCommandToolCall", "terminalToolCall"):
        shell_call = tool_call.get(shell_key)
        if not isinstance(shell_call, dict):
            continue
        args = shell_call.get("args") if isinstance(shell_call.get("args"), dict) else {}
        command = str(args.get("command") or args.get("commandLine") or "").strip()
        if not command:
            break
        output = _shell_output_from_result(shell_call.get("result"))
        return _terminal_block(command, output)

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


def _collapse_echo_text(text: str) -> str:
    """Drop a single-chunk assistant payload that repeats itself back-to-back."""
    if not text:
        return text
    stripped = text.strip()
    if not stripped:
        return text
    if len(text) >= len(stripped) * 2:
        mid = len(text) // 2
        left = text[:mid].strip()
        right = text[mid:].strip()
        if left and left == right == stripped:
            return stripped if text.startswith(stripped) else stripped
    if text == stripped + stripped or text == f"{stripped}{stripped}":
        return stripped
    return text


def assistant_text_delta(accumulated: str, incoming: str) -> str:
    """Return only the suffix of *incoming* that is not already in *accumulated*.

    Cursor CLI with ``--stream-partial-output`` emits incremental assistant chunks
    (e.g. ``hello``, `` world``) and then a final aggregate event (``hello world``).
    Appending every event verbatim duplicates the full reply.
    """
    if not incoming:
        return ""
    if incoming == accumulated:
        return ""
    if accumulated and incoming.startswith(accumulated):
        suffix = incoming[len(accumulated) :]
        if not suffix:
            return ""
        # Cursor occasionally emits cumulative assistant text that repeats the
        # already-delivered prefix verbatim (e.g. "sentence A" -> "sentence A" + "sentence A").
        if suffix == accumulated or suffix.strip() == accumulated.strip():
            return ""
        return suffix
    if accumulated and accumulated.startswith(incoming):
        return ""
    return incoming


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
        self._assistant_accumulated = ""
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
            text = _collapse_echo_text(assistant_text_from_event(event))
            if text:
                delta = assistant_text_delta(self._assistant_accumulated, text)
                if delta:
                    self._saw_assistant_text = True
                    self._assistant_accumulated += delta
                    self._append(delta)
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
