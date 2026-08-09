"""Local Claude Code CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy
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


def _extract_claude_text(stream_text: str) -> tuple[str, str]:
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
    return final_text, error_text


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
        extracted, _error = _extract_claude_text(accumulated)
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
    output, error_text = _extract_claude_text(stdout)
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
