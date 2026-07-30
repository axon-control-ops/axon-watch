"""Shared local dispatch for Claude and Codex runtime families."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.claude_agent import run_claude_local
from app.cli_runtime.codex_agent import run_codex_local


def run_non_cursor_local(
    *,
    family: str,
    binary: str,
    prompt: str,
    workspace_root: Path,
    composer_mode: str,
    execution_tier: str,
    model: str,
    subprocess_env: dict[str, str],
    run_id: str,
    on_chunk: Callable[[str, str], None] | None,
    approval_notice: str | None,
) -> str:
    runner = run_claude_local if family == "claude" else run_codex_local
    content = runner(
        binary=binary,
        prompt=prompt,
        workspace_root=workspace_root,
        composer_mode=composer_mode,
        execution_tier=execution_tier,
        model=model,
        subprocess_env=subprocess_env,
        run_id=run_id,
        on_chunk=on_chunk,
    )
    if approval_notice:
        return f"{content.rstrip()}\n\n---\n{approval_notice}"
    return content
