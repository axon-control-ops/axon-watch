"""Local Cursor CLI runtime adapter for IDE composer requests."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import logging
from pathlib import Path
import time

from app.cli_runtime.cursor_stream_events import CursorStreamAssembler
from app.cli_runtime.research_mcp import ensure_workspace_research_mcp
from app.research.availability import research_capability_snapshot
from app.cli_runtime.subprocess_runner import (
    RuntimeProcessStoppedError,
    communicate_registered_process,
    raise_if_operator_stopped,
    stream_registered_process,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CursorAgentReply:
    content: str
    generated_image_paths: tuple[str, ...] = ()


def is_recursion_depth_error(detail: str | None) -> bool:
    """True when Cursor/CLI failed with Python's recursion-depth message."""
    text = " ".join(str(detail or "").lower().split())
    return "maximum recursion depth exceeded" in text


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


def build_cursor_agent_command(
    *,
    binary: str,
    prompt: str,
    workspace_root: Path | None,
    composer_mode: str,
    execution_tier: str = "consultative",
    model: str = "",
    trust_policy: str = "operator",
    research_available: bool | None = None,
) -> list[str]:
    """Build the Cursor CLI argv for operator vs continuous-worker trust policies."""
    command = [
        binary,
        "agent",
        "--print",
        "--trust",
        "--output-format",
        "stream-json",
        "--stream-partial-output",
    ]
    policy = str(trust_policy or "operator").strip().lower() or "operator"
    if research_available is None:
        research_available = bool(research_capability_snapshot().get("available"))
    if research_available and workspace_root:
        ensure_workspace_research_mcp(workspace_root)
    if policy != "worker" and research_available:
        # Cursor CLI rejects audited MCP tools unless --force is set alongside
        # --approve-mcps in headless dispatch (verified against cursor 3.10.x).
        command.extend(["--force", "--approve-mcps"])
    mode_flag = _cursor_mode_flag(composer_mode, execution_tier)
    if mode_flag:
        command.extend(["--mode", mode_flag])
    if workspace_root:
        # Safe-improvement evaluation must pass the disposable isolation root
        # (proposal_service.sandbox_agent_workspace), never the live bound project.
        command.extend(["--workspace", str(workspace_root.resolve())])
    if model:
        command.extend(["--model", model])
    command.append(prompt)
    return command


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
    trust_policy: str = "operator",
    research_available: bool | None = None,
) -> CursorAgentReply:
    # stream-json is the only print format that reliably carries assistant text;
    # `--output-format text` returns an empty body for plan/tool-heavy replies.
    command = build_cursor_agent_command(
        binary=binary,
        prompt=prompt,
        workspace_root=workspace_root,
        composer_mode=composer_mode,
        execution_tier=execution_tier,
        model=model,
        trust_policy=trust_policy,
        research_available=research_available,
    )

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


def run_cursor_local_with_recursion_retry(
    *,
    runtime_id: str,
    workspace_id: str,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str,
    model: str,
    subprocess_env: dict[str, str] | None,
    run_id: str,
    on_chunk: Callable[[str, str], None] | None,
    trust_policy: str,
) -> CursorAgentReply:
    """Run Cursor once, retrying recursion crashes without research MCP."""
    started = time.perf_counter()
    try:
        return run_cursor_local(
            binary=binary,
            prompt=prompt,
            workspace_root=workspace_root,
            composer_mode=composer_mode,
            execution_tier=execution_tier,
            model=model,
            subprocess_env=subprocess_env,
            run_id=run_id,
            on_chunk=on_chunk,
            trust_policy=trust_policy,
        )
    except RuntimeError as exc:
        if isinstance(exc, RuntimeProcessStoppedError) or not is_recursion_depth_error(str(exc)):
            raise
        logger.exception(
            "lane_b_dispatch_recursion runtime_id=%s composer_mode=%s "
            "workspace_id=%s elapsed_ms=%.0f; retrying without research MCP",
            runtime_id,
            composer_mode,
            workspace_id,
            (time.perf_counter() - started) * 1000,
        )
        return run_cursor_local(
            binary=binary,
            prompt=prompt,
            workspace_root=workspace_root,
            composer_mode=composer_mode,
            execution_tier=execution_tier,
            model=model,
            subprocess_env=subprocess_env,
            run_id=run_id,
            on_chunk=on_chunk,
            trust_policy=trust_policy,
            research_available=False,
        )
