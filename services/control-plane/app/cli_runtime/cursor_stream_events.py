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
import re
from typing import Any, Callable

from app.cli_runtime.research_stream_blocks import (
    normalize_transcript_content,
    research_completed_block_from_event,
    research_items_from_result,
    research_query_from_tool_call,
    research_started_block_from_event,
)
from app.cli_runtime.stream_blocks.terminal_blocks import (
    _relative_path,
    shell_command_from_tool_call,
    shell_completion_from_event,
    terminal_block,
    terminal_close_body,
    terminal_started_block_from_event,
)
from app.cli_runtime.stream_blocks.text_delta import assistant_text_delta
from app.cli_runtime.stream_blocks.transcript_dedupe import collapse_duplicated_body
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



_TERMINAL_OUTPUT_LIMIT = 4000



def image_block_from_event(
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


_EDIT_FAILURE_FALLBACK = (
    "Edit was rejected — the path may be outside your sandbox write scope, "
    "the patch may not apply cleanly, or the file may be read-only."
)


def _edit_failure_reason(result: dict[str, Any]) -> str:
    """Extract a human-readable edit failure from Cursor stream-json result shapes."""
    reasons: list[str] = []
    error = result.get("error")
    if isinstance(error, dict):
        for key in ("userMessage", "user_message", "agentMessage", "agent_message", "message"):
            value = error.get(key)
            if isinstance(value, str) and value.strip():
                reasons.append(value.strip())
                break
        if not reasons:
            nested = str(error.get("detail") or error.get("reason") or "").strip()
            if nested:
                reasons.append(nested)
    elif isinstance(error, str) and error.strip():
        reasons.append(error.strip())

    for key in ("userMessage", "user_message", "agentMessage", "agent_message", "message", "reason", "detail"):
        value = result.get(key)
        if isinstance(value, str) and value.strip():
            reasons.append(value.strip())

    rejected = result.get("rejected")
    if isinstance(rejected, dict):
        for key in ("reason", "message", "detail"):
            value = rejected.get(key)
            if isinstance(value, str) and value.strip():
                reasons.append(value.strip())

    deduped: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        normalized = " ".join(reason.split())
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped[0] if deduped else _EDIT_FAILURE_FALLBACK


def edit_block_from_tool_call(edit: dict[str, Any], workspace_root: str) -> str:
    """Render a completed editToolCall as an edit or edit-failed fence."""
    args = edit.get("args") if isinstance(edit.get("args"), dict) else {}
    result = edit.get("result") if isinstance(edit.get("result"), dict) else {}
    success = result.get("success") if isinstance(result.get("success"), dict) else None
    path = _relative_path(str((success or args).get("path") or args.get("path") or ""), workspace_root)
    if not isinstance(success, dict):
        reason = _edit_failure_reason(result)
        return f"\n:::edit-failed {path}\n{reason}\n:::\n"
    added = int(success.get("linesAdded") or 0)
    removed = int(success.get("linesRemoved") or 0)
    diff = str(success.get("diffString") or "").strip()
    return f"\n:::edit {path} +{added} -{removed}\n{diff}\n:::\n"


def tool_block_from_event(
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

    image_block = image_block_from_event(event, workspace_root)
    if image_block:
        return image_block

    edit = tool_call.get("editToolCall")
    if isinstance(edit, dict):
        return edit_block_from_tool_call(edit, workspace_root)

    read = tool_call.get("readToolCall")
    if isinstance(read, dict):
        args = read.get("args") if isinstance(read.get("args"), dict) else {}
        path = _relative_path(str(args.get("path") or ""), workspace_root)
        return f"\n:::tool Read {path}\n"

    shell_completion = shell_completion_from_event(event)
    if shell_completion is not None:
        command, output = shell_completion
        return terminal_block(command, output)

    for key, value in tool_call.items():
        if not key.endswith("ToolCall") or not isinstance(value, dict):
            continue
        # str.capitalize() lowercases the rest of the string, so a camelCase key
        # like "askQuestionToolCall" rendered as "Askquestion" instead of
        # "Ask Question" — split on the case boundary first, then title-case.
        raw_label = re.sub(r"(?<!^)(?=[A-Z])", " ", key[: -len("ToolCall")])
        label = raw_label.replace("_", " ").title()
        args = value.get("args") if isinstance(value.get("args"), dict) else {}
        target = str(args.get("path") or args.get("command") or "").strip()
        target = _relative_path(target, workspace_root)
        if not target:
            # Tools like AskQuestion/CreatePlan carry their real payload (the
            # question/plan text) under a tool-specific key rather than
            # path/command — surface the first plain string arg we find so the
            # block isn't a bare, contentless header. The model is instructed
            # not to call these tools at all (see ask_fence_instruction); this
            # is a fallback for when it does anyway.
            for arg_value in args.values():
                if isinstance(arg_value, str) and arg_value.strip():
                    target = arg_value.strip()
                    break
        suffix = f" {target}" if target else ""
        return f"\n:::tool {label}{suffix}\n"
    return ""


def collapse_echo_text(text: str) -> str:
    return collapse_duplicated_body(text)



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
        self._thinking_accumulated = ""
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
        self._thinking_accumulated = ""

    def _close_open_research(self) -> None:
        if self._research_open_active:
            self._append("\n:::\n")
            self._research_open_query = None
            self._research_open_active = False

    def _close_open_terminal(self, *, output: str = "") -> None:
        if not self._terminal_open_active:
            return
        self._append(terminal_close_body(output))
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
            # Cursor can emit incremental thinking chunks and then a cumulative
            # echo of the full block — same failure mode as assistant text.
            incoming = collapse_echo_text(str(event.get("text") or ""))
            if incoming:
                delta = assistant_text_delta(self._thinking_accumulated, incoming)
                if delta:
                    if not self._thinking_open:
                        self._append("\n:::thinking\n")
                        self._thinking_open = True
                    self._thinking_accumulated += delta
                    self._append(delta)
            return

        if event_type == "assistant":
            self._close_thinking()
            text = collapse_echo_text(assistant_text_from_event(event))
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
                        self._terminal_open_command = shell_command_from_tool_call(tool_call) or None
                        self._terminal_open_active = True
                    return
            if subtype == "completed":
                for image_path in image_paths_from_tool_call_event(event):
                    if image_path not in self._generated_image_paths:
                        self._generated_image_paths.append(image_path)
                shell_completion = shell_completion_from_event(event)
                if shell_completion is not None:
                    command, output = shell_completion
                    if self._terminal_open_active:
                        self._close_open_terminal(output=output)
                    else:
                        self._append(terminal_block(command, output))
                    return
                open_query = self._research_open_query if self._research_open_active else None
                block = tool_block_from_event(
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
        raw_content = self.content.strip()
        content = normalize_transcript_content(raw_content)
        if not self._saw_assistant_text and self.result_text and not content:
            return normalize_transcript_content(self.result_text.strip())
        return content


# Backward-compatible exports for tests.
def _research_items_from_result(result: Any) -> list[dict[str, str]]:
    return research_items_from_result(result)