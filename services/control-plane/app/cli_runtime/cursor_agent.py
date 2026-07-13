"""Local Cursor CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.cli_runtime.cursor_stream_events import CursorStreamAssembler
from app.cli_runtime.research_mcp import ensure_workspace_research_mcp
from app.research.availability import research_capability_snapshot
from app.cli_runtime.subprocess_runner import (
    RuntimeProcessStoppedError,
    communicate_registered_process,
    raise_if_operator_stopped,
    stream_registered_process,
)


@dataclass(frozen=True)
class CursorAgentReply:
    content: str
    generated_image_paths: tuple[str, ...] = ()


def _cursor_mode_flag(composer_mode: str, execution_tier: str) -> str:
    """Cursor CLI only accepts --mode plan|ask; full agent mode is the default (no flag).

    Debug uses the same flags as Agent: consultative → plan (read-only), executing → no flag.
    The Debug evidence loop is enforced via the system prompt, not a CLI mode flag.
    """
    if composer_mode == "ask":
        return "ask"
    if composer_mode == "plan":
        return "plan"
    if execution_tier == "executing":
        return ""
    return "plan"


def run_cursor_local(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    timeout_seconds: int = 240,
    subprocess_env: dict[str, str] | None = None,
    run_id: str = "",
    on_chunk: Callable[[str, str], None] | None = None,
) -> CursorAgentReply:
    # stream-json is the only print format that reliably carries assistant text;
    # `--output-format text` returns an empty body for plan/tool-heavy replies.
    command = [
        binary,
        "agent",
        "--print",
        "--trust",
        "--output-format",
        "stream-json",
        "--stream-partial-output",
    ]
    if research_capability_snapshot().get("available"):
        # Cursor CLI rejects audited MCP tools unless --force is set alongside
        # --approve-mcps in headless dispatch (verified against cursor 3.10.x).
        command.extend(["--force", "--approve-mcps"])
        if workspace_root:
            ensure_workspace_research_mcp(workspace_root)
    mode_flag = _cursor_mode_flag(composer_mode, execution_tier)
    if mode_flag:
        command.extend(["--mode", mode_flag])
    if workspace_root:
        command.extend(["--workspace", str(workspace_root.resolve())])
    if model:
        command.extend(["--model", model])
    command.append(prompt)

    assembler = CursorStreamAssembler(
        workspace_root=str(workspace_root.resolve() if workspace_root else ""),
        on_delta=on_chunk,
    )
    run_cwd = str(workspace_root.resolve()) if workspace_root else None

    def handle_raw_chunk(_accumulated_raw: str, raw_line: str) -> None:
        assembler.feed_line(raw_line)

    try:
        if on_chunk is not None:
            stdout, stderr, returncode = stream_registered_process(
                run_id=run_id,
                command=command,
                timeout_seconds=timeout_seconds,
                subprocess_env=subprocess_env,
                on_chunk=handle_raw_chunk,
                cwd=run_cwd,
            )
        else:
            stdout, stderr, returncode = communicate_registered_process(
                run_id=run_id,
                command=command,
                timeout_seconds=timeout_seconds,
                subprocess_env=subprocess_env,
                cwd=run_cwd,
            )
            for line in stdout.splitlines():
                assembler.feed_line(line)
    except RuntimeProcessStoppedError:
        raise
    except RuntimeError:
        raise
    raise_if_operator_stopped(returncode=returncode, stderr=stderr, stdout=stdout)
    reply = assembler.finalize()
    if returncode != 0:
        raise RuntimeError(
            assembler.error_text
            or stderr.strip()
            or f"Cursor CLI exited with status {returncode}."
        )
    if assembler.error_text:
        raise RuntimeError(assembler.error_text)
    if not reply:
        raise RuntimeError("Cursor CLI returned no output.")
    return CursorAgentReply(
        content=reply,
        generated_image_paths=assembler.generated_image_paths,
    )
