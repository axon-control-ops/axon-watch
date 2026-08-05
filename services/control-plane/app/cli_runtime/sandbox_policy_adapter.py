"""Adapt effective employee authority to the generic process sandbox."""

from __future__ import annotations

from pathlib import Path

from app.cli_runtime.agent_sandbox import AgentSandboxPolicy
from app.workspace_agents.execution_policy import AgentExecutionPolicy


def _runtime_paths(binary: str, *, include_cursor_auth: bool) -> tuple[str, ...]:
    executable = Path(binary).expanduser().resolve(strict=True)
    home = Path.home().resolve()
    paths: list[Path] = [executable.parent]
    if include_cursor_auth:
        for candidate in (
            home / ".cursor" / "cli-config.json",
            home / ".cursor" / "agent-cli-state.json",
            home / ".config" / "cursor" / "auth.json",
        ):
            if candidate.is_file():
                paths.append(candidate)
    return tuple(str(path) for path in paths)


def adapt_execution_policy(
    policy: AgentExecutionPolicy,
    *,
    runtime_binary: str,
    include_cursor_auth: bool = False,
) -> AgentSandboxPolicy:
    return AgentSandboxPolicy(
        writable_roots=policy.write_paths,
        approved_wrappers=policy.approved_wrapper_names,
        approved_command_prefixes=policy.approved_command_prefixes,
        forbidden_path_globs=policy.forbidden_path_globs,
        cursor_readonly_paths=_runtime_paths(
            runtime_binary,
            include_cursor_auth=include_cursor_auth,
        ),
    )


def sandbox_agent_env(
    env: dict[str, str],
    *,
    workspace_id: str,
    run_id: str,
) -> dict[str, str]:
    return {
        **env,
        "AXON_AGENT_SOURCE_WORKSPACE_ID": workspace_id,
        "AXON_WATCH_WORKSPACE_ID": workspace_id,
        "AXON_WATCH_RUN_ID": run_id,
    }


def prepare_execution_sandbox(
    policy: AgentExecutionPolicy | None,
    *,
    family: str,
    runtime_binary: str,
    env: dict[str, str],
    workspace_id: str,
    run_id: str,
) -> tuple[dict[str, str], AgentSandboxPolicy | None]:
    if policy is None:
        return env, None
    return (
        sandbox_agent_env(env, workspace_id=workspace_id, run_id=run_id),
        adapt_execution_policy(
            policy,
            runtime_binary=runtime_binary,
            include_cursor_auth=family == "cursor",
        ),
    )


__all__ = [
    "adapt_execution_policy",
    "prepare_execution_sandbox",
    "sandbox_agent_env",
]
