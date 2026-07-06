"""Local Codex CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.subprocess_runner import (
    RuntimeProcessStoppedError,
    communicate_registered_process,
    raise_if_operator_stopped,
    stream_registered_process,
)


def _build_codex_exec_command(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
) -> list[str]:
    command = [binary, "exec", "--json", "--ephemeral"]
    if workspace_root:
        command.extend(["-C", str(workspace_root), "--skip-git-repo-check"])
    if execution_tier == "executing":
        command.extend(["--sandbox", "workspace-write", "-c", 'approval_policy="on-request"'])
    else:
        command.extend(["--sandbox", "read-only", "-c", 'approval_policy="never"'])
    if model:
        command.extend(["--model", model])
    command.append("--")
    command.append(prompt)
    return command


def _extract_codex_text(stream_text: str) -> str:
    final_text = ""
    for raw_line in str(stream_text or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            final_text = line
            continue
        if not isinstance(payload, dict):
            continue
        if payload.get("type") != "item.completed":
            continue
        item = payload.get("item")
        if not isinstance(item, dict):
            continue
        if item.get("type") != "agent_message":
            continue
        text = str(item.get("text") or "").strip()
        if text:
            final_text = text
    return final_text


def run_codex_local(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    timeout_seconds: int = 90,
    subprocess_env: dict[str, str] | None = None,
    run_id: str = "",
    on_chunk: Callable[[str, str], None] | None = None,
) -> str:
    command = _build_codex_exec_command(
        binary=binary,
        prompt=prompt,
        workspace_root=workspace_root,
        composer_mode=composer_mode,
        execution_tier=execution_tier,
        model=model,
    )

    def _emit_codex_chunk(accumulated: str, delta: str) -> None:
        if on_chunk is None:
            return
        extracted = _extract_codex_text(accumulated)
        if extracted:
            on_chunk(extracted, delta)

    runner = stream_registered_process if on_chunk is not None else communicate_registered_process
    try:
        stdout, stderr, returncode = runner(
            run_id=run_id,
            command=command,
            timeout_seconds=timeout_seconds,
            subprocess_env=subprocess_env,
            **({"on_chunk": _emit_codex_chunk} if on_chunk is not None else {}),
        )
    except RuntimeProcessStoppedError:
        raise
    except RuntimeError:
        raise
    raise_if_operator_stopped(returncode=returncode, stderr=stderr, stdout=stdout)
    output = _extract_codex_text(stdout)
    if not output:
        output = stdout.strip() or stderr.strip()
    if returncode != 0:
        raise RuntimeError(output or f"Codex CLI exited with status {returncode}.")
    if not output:
        raise RuntimeError("Codex CLI returned no output.")
    return output
