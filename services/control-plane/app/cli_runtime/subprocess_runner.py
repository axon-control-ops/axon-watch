"""Shared subprocess execution with optional run-scoped cancellation."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Callable
from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy, wrap_command_in_agent_sandbox
from app.cli_runtime.process_registry import register, unregister
from app.cli_runtime.agent_process_scope import wrap_command_in_agent_scope
from app.cli_runtime.user_bin_path import runtime_path_with_user_bins

# Match workspace PTY defaults so headless Cursor/agent shell tools can run
# ``tput`` / color-aware scripts without ``No value for $TERM``.
_HEADLESS_TERM = "xterm-256color"
_HEADLESS_COLORTERM = "truecolor"


class RuntimeProcessStoppedError(RuntimeError):
    pass


def headless_cli_env(subprocess_env: dict[str, str] | None = None) -> dict[str, str]:
    """Build env for non-interactive agent CLIs (Cursor/Claude/Codex).

    Control-plane services often inherit a bare systemd environment with no
    ``TERM``. Agents then fail scripts that call ``tput``, leaving the Team
    panel in a red "Last job failed" state even when the code work finished.
    """
    env = {**(subprocess_env or os.environ)}
    env["NO_COLOR"] = "1"
    env["PATH"] = runtime_path_with_user_bins(str(env.get("PATH") or ""))
    if not str(env.get("TERM") or "").strip():
        env["TERM"] = _HEADLESS_TERM
    if not str(env.get("COLORTERM") or "").strip():
        env["COLORTERM"] = _HEADLESS_COLORTERM
    return env


def _prepare_command(
    command: list[str],
    *,
    sandbox_policy: AgentSandboxPolicy | None,
    cwd: str | os.PathLike[str] | None,
    run_id: str,
) -> list[str]:
    if sandbox_policy is None:
        return wrap_command_in_agent_scope(command)
    if cwd is None:
        raise RuntimeError("Sandboxed agent execution requires a workspace root.")
    sandbox_command = list(command)
    executable = Path(sandbox_command[0]).expanduser()
    if executable.is_absolute():
        sandbox_command[0] = str(executable.resolve(strict=True))
    launch = wrap_command_in_agent_sandbox(
        sandbox_command,
        policy=sandbox_policy,
        workspace_root=Path(cwd),
        run_id=run_id,
    )
    from app.runs.service import append_run_execution_receipt

    append_run_execution_receipt(
        run_id,
        receipt_type="agent_sandbox_started",
        receipt_summary=f"Bubblewrap and immutable hooks active ({launch.hook_material.policy_id})",
        actor="cli_runtime",
        success=True,
        intent="sandbox_startup",
    )
    return wrap_command_in_agent_scope(list(launch.command))


def communicate_registered_process(
    *,
    run_id: str,
    command: list[str],
    timeout_seconds: int,
    subprocess_env: dict[str, str] | None = None,
    cwd: str | os.PathLike[str] | None = None,
    sandbox_policy: AgentSandboxPolicy | None = None,
) -> tuple[str, str, int]:
    env = headless_cli_env(subprocess_env)
    proc = subprocess.Popen(
        _prepare_command(
            command,
            sandbox_policy=sandbox_policy,
            cwd=cwd,
            run_id=run_id,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        cwd=cwd or None,
    )
    clean_run_id = str(run_id or "").strip()
    if clean_run_id:
        register(clean_run_id, proc)
    try:
        stdout, stderr = proc.communicate(timeout=timeout_seconds)
        returncode = int(proc.returncode or 0)
        return stdout or "", stderr or "", returncode
    except subprocess.TimeoutExpired as exc:
        proc.kill()
        proc.communicate(timeout=5)
        raise RuntimeError(f"CLI runtime timed out after {timeout_seconds}s.") from exc
    finally:
        if clean_run_id:
            unregister(clean_run_id)


def stream_registered_process(
    *,
    run_id: str,
    command: list[str],
    timeout_seconds: int,
    subprocess_env: dict[str, str] | None = None,
    on_chunk: Callable[[str, str], None] | None = None,
    cwd: str | os.PathLike[str] | None = None,
    sandbox_policy: AgentSandboxPolicy | None = None,
) -> tuple[str, str, int]:
    env = headless_cli_env(subprocess_env)
    proc = subprocess.Popen(
        _prepare_command(
            command,
            sandbox_policy=sandbox_policy,
            cwd=cwd,
            run_id=run_id,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=env,
        cwd=cwd or None,
    )
    clean_run_id = str(run_id or "").strip()
    if clean_run_id:
        register(clean_run_id, proc)
    accumulated = ""
    try:
        if proc.stdout is not None:
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                accumulated += line
                if on_chunk is not None:
                    on_chunk(accumulated, line)
        try:
            proc.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            proc.communicate(timeout=5)
            raise RuntimeError(f"CLI runtime timed out after {timeout_seconds}s.") from exc
        stderr = proc.stderr.read() if proc.stderr is not None else ""
        returncode = int(proc.returncode or 0)
        return accumulated, stderr or "", returncode
    finally:
        if clean_run_id:
            unregister(clean_run_id)


def raise_if_operator_stopped(*, returncode: int, stderr: str, stdout: str) -> None:
    if returncode < 0:
        raise RuntimeProcessStoppedError(
            "Runtime execution stopped by operator before the CLI finished."
        )
    if returncode != 0 and "stopped by operator" in f"{stdout}\n{stderr}".lower():
        raise RuntimeProcessStoppedError(
            "Runtime execution stopped by operator before the CLI finished."
        )
