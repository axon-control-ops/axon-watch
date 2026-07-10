"""Parse Cursor CLI stream-json events into Cursor-style transcript blocks.

The assembled reply uses fenced block markers the console renders specially:

    :::thinking
    ...reasoning text...
    :::

    :::image assets/mockup.png
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

from app.cli_runtime.research_stream_blocks import (
    collapse_duplicated_body,
    normalize_transcript_content,
    research_completed_block_from_event,
    research_items_from_result,
    research_query_from_tool_call,
    research_started_block_from_event,
)
from app.cli_runtime.generated_image_paths import image_paths_from_tool_call_event


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
        if basename:
            if (root / basename).is_file():
                return basename
            if (root / "assets" / basename).is_file():
                return f"assets/{basename}"
            return basename

    parts = resolved.as_posix().split("/")
    if "README.md" in parts:
        return "README.md"
    return resolved.name or path


_TERMINAL_OUTPUT_LIMIT = 4000


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


_SHELL_TOOL_KEYS = ("shellToolCall", "runTerminalCommandToolCall", "terminalToolCall")


def _shell_command_from_tool_call(tool_call: dict[str, Any]) -> str:
    for shell_key in _SHELL_TOOL_KEYS:
        shell_call = tool_call.get(shell_key)
        if not isinstance(shell_call, dict):
            continue
        args = shell_call.get("args") if isinstance(shell_call.get("args"), dict) else {}
        command = str(args.get("command") or args.get("commandLine") or "").strip()
        if command:
            return command
    return ""


def _shell_call_from_tool_call(tool_call: dict[str, Any]) -> dict[str, Any] | None:
    for shell_key in _SHELL_TOOL_KEYS:
        shell_call = tool_call.get(shell_key)
        if isinstance(shell_call, dict):
            return shell_call
    return None


def _terminal_block(command: str, output: str) -> str:
    trimmed = output.strip()
    if len(trimmed) > _TERMINAL_OUTPUT_LIMIT:
        trimmed = f"{trimmed[:_TERMINAL_OUTPUT_LIMIT].rstrip()}\n… (output truncated)"
    body = f"\n{trimmed}\n" if trimmed else "\n"
    return f"\n:::terminal {command}{body}:::\n"


def _terminal_started_block(command: str) -> str:
    trimmed = command.strip()
    if not trimmed:
        return ""
    return f"\n:::terminal {trimmed}\n"


def _terminal_close_body(output: str) -> str:
    trimmed = output.strip()
    if len(trimmed) > _TERMINAL_OUTPUT_LIMIT:
        trimmed = f"{trimmed[:_TERMINAL_OUTPUT_LIMIT].rstrip()}\n… (output truncated)"
    if trimmed:
        return f"{trimmed}\n:::\n"
    return ":::\n"


def terminal_started_block_from_event(event: dict[str, Any]) -> str:
    """Open a live `:::terminal` block when a shell tool call starts (Cursor parity)."""
    if event.get("type") != "tool_call" or event.get("subtype") != "started":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""
    return _terminal_started_block(_shell_command_from_tool_call(tool_call))


def _shell_completion_from_event(event: dict[str, Any]) -> tuple[str, str] | None:
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return None
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return None
    shell_call = _shell_call_from_tool_call(tool_call)
    if shell_call is None:
        return None
    command = _shell_command_from_tool_call(tool_call)
    if not command:
        return None
    output = _shell_output_from_result(shell_call.get("result"))
    return command, output


def _image_block_from_event(
    event: dict[str, Any],
    workspace_root: str,
) -> str:
    paths = image_paths_from_tool_call_event(event)
    if not paths:
        return ""
    blocks: list[str] = []
    for raw_path in paths:
        path = _relative_path(raw_path, workspace_root)
        if path:
            blocks.append(f"\n:::image {path}\n:::\n")
    return "".join(blocks)


def _tool_block_from_event(
    event: dict[str, Any],
    workspace_root: str,
    *,
    open_query: str | None = None,
) -> str:
    """Render a completed tool_call event as a transcript block, or ''."""
    if event.get("type") != "tool_call" or event.get("subtype") != "completed":
        return ""
    tool_call = event.get("tool_call")
    if not isinstance(tool_call, dict):
        return ""

    research_block = research_completed_block_from_event(event, open_query=open_query)
    if research_block:
        return research_block

    image_block = _image_block_from_event(event, workspace_root)
    if image_block:
        return image_block

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

    shell_completion = _shell_completion_from_event(event)
    if shell_completion is not None:
        command, output = shell_completion
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
    return collapse_duplicated_body(text)


def assistant_text_delta(accumulated: str, incoming: str) -> str:
    """Return only the suffix of *incoming* that is not already in *accumulated*.

    Cursor CLI with ``--stream-partial-output`` emits incremental assistant chunks
    (e.g. ``hello``, `` world``) and then a final aggregate event (``hello world``).
    Appending every event verbatim duplicates the full reply.
    """
    incoming = collapse_duplicated_body(incoming)
    if not incoming:
        return ""
    if incoming == accumulated:
        return ""
    if accumulated and incoming.startswith(accumulated):
        suffix = incoming[len(accumulated) :]
        if not suffix:
            return ""
        if suffix == accumulated or suffix.strip() == accumulated.strip():
            return ""
        collapsed_combined = collapse_duplicated_body(accumulated + suffix)
        if collapsed_combined.strip() == accumulated.strip():
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
        self._research_open_query: str | None = None
        self._research_open_active = False
        self._terminal_open_command: str | None = None
        self._terminal_open_active = False
        self._generated_image_paths: list[str] = []
        self.result_text = ""
        self.error_text = ""

    @property
    def generated_image_paths(self) -> tuple[str, ...]:
        return tuple(self._generated_image_paths)

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

    def _close_open_research(self) -> None:
        if self._research_open_active:
            self._append("\n:::\n")
            self._research_open_query = None
            self._research_open_active = False

    def _close_open_terminal(self, *, output: str = "") -> None:
        if not self._terminal_open_active:
            return
        self._append(_terminal_close_body(output))
        self._terminal_open_command = None
        self._terminal_open_active = False

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
            subtype = str(event.get("subtype") or "")
            if subtype == "started":
                started = research_started_block_from_event(event)
                if started:
                    self._close_open_terminal()
                    self._close_open_research()
                    self._append(started)
                    tool_call = event.get("tool_call")
                    if isinstance(tool_call, dict):
                        self._research_open_query = research_query_from_tool_call(tool_call) or "Research"
                        self._research_open_active = True
                    return
                terminal_started = terminal_started_block_from_event(event)
                if terminal_started:
                    self._close_open_research()
                    self._close_open_terminal()
                    self._append(terminal_started)
                    tool_call = event.get("tool_call")
                    if isinstance(tool_call, dict):
                        self._terminal_open_command = _shell_command_from_tool_call(tool_call) or None
                        self._terminal_open_active = True
                    return
            if subtype == "completed":
                for image_path in image_paths_from_tool_call_event(event):
                    if image_path not in self._generated_image_paths:
                        self._generated_image_paths.append(image_path)
                shell_completion = _shell_completion_from_event(event)
                if shell_completion is not None:
                    command, output = shell_completion
                    if self._terminal_open_active:
                        self._close_open_terminal(output=output)
                    else:
                        self._append(_terminal_block(command, output))
                    return
                open_query = self._research_open_query if self._research_open_active else None
                block = _tool_block_from_event(
                    event,
                    self._workspace_root,
                    open_query=open_query,
                )
                if block:
                    self._append(block)
                    self._research_open_query = None
                    self._research_open_active = False
                return
            return

        result = result_from_event(event)
        if result is not None:
            self._close_thinking()
            self.result_text, is_error = result
            if is_error:
                self.error_text = self.result_text or "Cursor CLI reported an error result."

    def finalize(self) -> str:
        self._close_thinking()
        self._close_open_research()
        self._close_open_terminal()
        content = normalize_transcript_content(self.content.strip())
        if not self._saw_assistant_text and self.result_text and not content:
            return normalize_transcript_content(self.result_text.strip())
        return content


# Backward-compatible exports for tests.
def _research_items_from_result(result: Any) -> list[dict[str, str]]:
    return research_items_from_result(result)
