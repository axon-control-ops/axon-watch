"""Local Claude Code CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

import json
from difflib import unified_diff
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy
from app.cli_runtime.stream_blocks.terminal_blocks import _relative_path, terminal_block
from app.cli_runtime.subprocess_runner import (
    RuntimeProcessStoppedError,
    communicate_registered_process,
    raise_if_operator_stopped,
    stream_registered_process,
)


def _claude_permission_mode(composer_mode: str, execution_tier: str) -> str:
    """Map Axon composer modes onto Claude Code permission modes."""
    if composer_mode in {"ask", "plan"}:
        return "plan"
    if execution_tier == "executing":
        return "acceptEdits"
    return "plan"


_CLAUDE_EFFORT_LEVELS = frozenset({"low", "medium", "high", "xhigh", "max"})


def build_claude_agent_command(
    *,
    binary: str,
    prompt: str,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    reasoning_effort: str = "",
) -> list[str]:
    """Build the Claude Code argv for headless Lane B dispatch."""
    command = [
        binary,
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--include-partial-messages",
        "--no-session-persistence",
        "--permission-mode",
        _claude_permission_mode(composer_mode, execution_tier),
    ]
    if model:
        command.extend(["--model", model])
    effort = str(reasoning_effort or "").strip().lower()
    if effort and effort in _CLAUDE_EFFORT_LEVELS:
        command.extend(["--effort", effort])
    command.append(prompt)
    return command


def _text_from_content_blocks(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for block in content:
        if isinstance(block, str) and block.strip():
            parts.append(block.strip())
            continue
        if not isinstance(block, dict):
            continue
        if str(block.get("type") or "") in {"text", "output_text"}:
            text = str(block.get("text") or "").strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _text_from_payload(payload: dict[str, object]) -> str:
    event_type = str(payload.get("type") or "")
    if event_type == "result":
        if payload.get("is_error"):
            return ""
        result = payload.get("result")
        if isinstance(result, str) and result.strip():
            return result.strip()
        return _text_from_content_blocks(payload.get("content"))
    if event_type == "assistant":
        message = payload.get("message")
        if isinstance(message, dict):
            return _text_from_content_blocks(message.get("content"))
        return _text_from_content_blocks(payload.get("content"))
    if event_type in {"content_block_delta", "stream_event"}:
        delta = payload.get("delta")
        if isinstance(delta, dict) and str(delta.get("type") or "") in {
            "text_delta",
            "text",
        }:
            return str(delta.get("text") or "")
    return ""


def _error_from_payload(payload: dict[str, object]) -> str:
    event_type = str(payload.get("type") or "")
    if event_type == "result" and payload.get("is_error"):
        detail = str(payload.get("result") or payload.get("error") or "").strip()
        return detail or "Claude CLI returned an error result."
    if event_type == "system" and str(payload.get("subtype") or "") in {
        "error",
        "api_error",
    }:
        return str(payload.get("error") or payload.get("message") or "").strip()
    return ""


def _iter_json_payloads(stream_text: str) -> list[dict[str, object]]:
    text = str(stream_text or "").strip()
    if not text:
        return []
    payloads: list[dict[str, object]] = []
    if text.startswith("["):
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    payloads.append(item)
            return payloads
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads


def _claude_tool_transcript(stream_text: str, workspace_root: Path) -> str:
    """Turn Claude stream-json tool activity into the shared transcript blocks.

    Cursor already emits these blocks directly. Without this adapter, Claude
    tool use was invisible to every workspace despite Full Access being active.
    """
    emitted: set[str] = set()
    commands: dict[str, str] = {}
    blocks: list[str] = []
    for payload in _iter_json_payloads(stream_text):
        event_type = str(payload.get("type") or "")
        content: object = None
        if event_type == "assistant":
            message = payload.get("message")
            content = message.get("content") if isinstance(message, dict) else payload.get("content")
        elif event_type == "user":
            message = payload.get("message")
            content = message.get("content") if isinstance(message, dict) else payload.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = str(block.get("type") or "")
            if block_type == "tool_use":
                tool_id = str(block.get("id") or "").strip()
                if not tool_id or tool_id in emitted:
                    continue
                emitted.add(tool_id)
                name = str(block.get("name") or "Tool").strip()
                tool_input = block.get("input") if isinstance(block.get("input"), dict) else {}
                command = str(tool_input.get("command") or "").strip()
                if name.lower() in {"bash", "shell", "terminal"} and command:
                    commands[tool_id] = command
                    continue
                path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()
                relative_path = _relative_path(path, str(workspace_root)) if path else ""
                if name.lower() in {"edit", "write"} and relative_path:
                    before = str(tool_input.get("old_string") or "")
                    after = str(tool_input.get("new_string") or tool_input.get("content") or "")
                    diff = "\n".join(
                        unified_diff(
                            before.splitlines(), after.splitlines(),
                            fromfile=f"a/{relative_path}", tofile=f"b/{relative_path}", lineterm="",
                        )
                    )
                    added = sum(1 for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++"))
                    removed = sum(1 for line in diff.splitlines() if line.startswith("-") and not line.startswith("---"))
                    blocks.append(f"\n:::edit {relative_path} +{added} -{removed}\n{diff}\n:::\n")
                else:
                    suffix = f" {relative_path}" if relative_path else ""
                    blocks.append(f":::tool {name}{suffix}\n")
            elif block_type == "tool_result":
                tool_id = str(block.get("tool_use_id") or "").strip()
                command = commands.get(tool_id)
                if not command:
                    continue
                result = _text_from_content_blocks(block.get("content"))
                blocks.append(terminal_block(command, result))
                commands.pop(tool_id, None)
    # Keep in-progress commands visible in a live transcript even before their
    # tool_result message arrives.
    for command in commands.values():
        blocks.append(f"\n:::terminal {command}\n:::\n")
    return "".join(blocks).strip()


def _extract_claude_text(stream_text: str, workspace_root: Path | None = None) -> tuple[str, str]:
    """Return (assistant_text, error_text) from Claude Code stream-json/json output."""
    final_text = ""
    accumulated_deltas: list[str] = []
    error_text = ""
    for payload in _iter_json_payloads(stream_text):
        err = _error_from_payload(payload)
        if err:
            error_text = err
        text = _text_from_payload(payload)
        if not text:
            continue
        event_type = str(payload.get("type") or "")
        if event_type in {"content_block_delta", "stream_event"}:
            accumulated_deltas.append(text)
            continue
        final_text = text
    if not final_text and accumulated_deltas:
        final_text = "".join(accumulated_deltas).strip()
    transcript = _claude_tool_transcript(stream_text, workspace_root or Path.cwd())
    return "\n\n".join(part for part in (transcript, final_text) if part).strip(), error_text


def run_claude_local(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    reasoning_effort: str = "",
    timeout_seconds: int = 240,
    subprocess_env: dict[str, str] | None = None,
    run_id: str = "",
    on_chunk: Callable[[str, str], None] | None = None,
    sandbox_policy: AgentSandboxPolicy | None = None,
) -> str:
    command = build_claude_agent_command(
        binary=binary,
        prompt=prompt,
        composer_mode=composer_mode,
        execution_tier=execution_tier,
        model=model,
        reasoning_effort=reasoning_effort,
    )
    run_cwd = str(workspace_root.resolve()) if workspace_root else None

    def _emit_claude_chunk(accumulated: str, delta: str) -> None:
        if on_chunk is None:
            return
        extracted, _error = _extract_claude_text(accumulated, workspace_root)
        if extracted:
            on_chunk(extracted, delta)

    runner = stream_registered_process if on_chunk is not None else communicate_registered_process
    try:
        stdout, stderr, returncode = runner(
            run_id=run_id,
            command=command,
            timeout_seconds=timeout_seconds,
            subprocess_env=subprocess_env,
            cwd=run_cwd,
            sandbox_policy=sandbox_policy,
            **({"on_chunk": _emit_claude_chunk} if on_chunk is not None else {}),
        )
    except RuntimeProcessStoppedError:
        raise
    except RuntimeError:
        raise
    raise_if_operator_stopped(returncode=returncode, stderr=stderr, stdout=stdout)
    output, error_text = _extract_claude_text(stdout, workspace_root)
    if not output:
        output = stdout.strip() or stderr.strip()
    if returncode != 0:
        raise RuntimeError(
            error_text or output or f"Claude CLI exited with status {returncode}."
        )
    if error_text and not output:
        raise RuntimeError(error_text)
    if not output:
        raise RuntimeError("Claude CLI returned no output.")
    return output
