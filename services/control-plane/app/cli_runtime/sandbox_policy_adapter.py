"""Adapt effective employee authority to the generic process sandbox."""

from __future__ import annotations

from pathlib import Path

from app.cli_runtime.agent_dispatch_preflight import (
    validate_agent_dispatch_preflight,
    validate_sandbox_workspace_toolchain,
)
from app.cli_runtime.agent_sandbox import (
    CURSOR_WRITABLE_STATE_RELATIVE,
    AgentSandboxPolicy,
)
from app.workspace_agents.execution_policy import AgentExecutionPolicy


# Every runtime family persists its subscription/OAuth session in its own
# dotfile under $HOME. The sandbox rewrites HOME (see _SANDBOX_HOME in
# agent_sandbox.py), so unless that file is bind-mounted in too, a CLI that's
# fully logged in on the host sees no credentials at all inside the sandbox
# and fails every dispatch with "not logged in" — this was previously scoped
# to cursor only, so claude/codex sandboxed dispatch always failed auth
# regardless of host login state.
_AUTH_PATH_CANDIDATES: dict[str, tuple[str, ...]] = {
    "cursor": (
        ".config/cursor/auth.json",
    ),
    "claude": (".claude/.credentials.json",),
    # Codex uses the isolated CODEX_HOME supplied below; never mount desktop auth.
    "codex": (),
}


def _runtime_paths(binary: str, *, family: str) -> tuple[str, ...]:
    executable = Path(binary).expanduser().resolve(strict=True)
    home = Path.home().resolve()
    paths: list[Path] = [executable.parent]
    if executable.parent.name == "bin":
        # npm-managed CLIs (codex, claude) resolve their own sibling
        # optional/native dependencies via Node's module resolution, which
        # walks up from bin/ into the package root's own node_modules (e.g.
        # .../codex/node_modules/@openai/codex-linux-x64) — exposing only
        # bin/ leaves that lookup finding nothing inside the sandbox, which
        # codex's own error handling reports as "Missing optional dependency"
        # even though the real, unsandboxed install has it.
        paths.append(executable.parent.parent)
    writable_state = set(CURSOR_WRITABLE_STATE_RELATIVE)
    for relative in _AUTH_PATH_CANDIDATES.get(family, ()):
        if relative in writable_state:
            continue
        candidate = home / relative
        if candidate.is_file():
            paths.append(candidate)
    return tuple(str(path) for path in paths)


def _codex_profile_auth_path(env: dict[str, str]) -> str:
    raw_home = str(env.get("CODEX_HOME") or "").strip()
    if not raw_home:
        return ""
    try:
        candidate = (Path(raw_home).expanduser() / "auth.json").resolve(strict=True)
    except OSError:
        return ""
    return str(candidate) if candidate.is_file() and not candidate.is_symlink() else ""


def adapt_execution_policy(
    policy: AgentExecutionPolicy,
    *,
    runtime_binary: str,
    family: str = "",
    env: dict[str, str] | None = None,
    injected_env: tuple[tuple[str, str], ...] = (),
) -> AgentSandboxPolicy:
    return AgentSandboxPolicy(
        writable_roots=policy.write_paths,
        approved_wrappers=policy.approved_wrapper_names,
        approved_command_prefixes=policy.approved_command_prefixes,
        forbidden_path_globs=policy.forbidden_path_globs,
        cursor_readonly_paths=_runtime_paths(runtime_binary, family=family),
        codex_auth_path=_codex_profile_auth_path(env or {}) if family == "codex" else "",
        injected_env=injected_env,
        allow_all_tools=policy.allow_all_tools,
    )


def sandbox_agent_env(
    env: dict[str, str],
    *,
    workspace_id: str,
    run_id: str,
) -> dict[str, str]:
    from app.workspace_service_connections import resolve_workspace_live_env

    bridge_env = resolve_workspace_live_env(workspace_id)
    return {
        **env,
        **bridge_env,
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
    workspace_root: Path | str | None = None,
) -> tuple[dict[str, str], AgentSandboxPolicy | None]:
    if policy is None:
        return env, None
    sandbox_env = sandbox_agent_env(env, workspace_id=workspace_id, run_id=run_id)
    bridge_env = {
        key: value
        for key, value in sandbox_env.items()
        if key.startswith(("SUPABASE_", "YEDC_", "EXPO_PUBLIC_SUPABASE_"))
    }
    injected_env = tuple(sorted(bridge_env.items()))
    policy_value = adapt_execution_policy(
        policy,
        runtime_binary=runtime_binary,
        family=family,
        env=sandbox_env,
        injected_env=injected_env,
    )
    if family == "codex":
        # Bubblewrap hides host paths, including the persistent Axon-X profile.
        # Codex must therefore use the actual private directory that the
        # sandbox materializes below. Its optional auth.json is read-only bound
        # there by AgentSandboxPolicy.codex_auth_path.
        sandbox_env["CODEX_HOME"] = "/run/axon-agent-home/.codex"
    validate_agent_dispatch_preflight(
        family=family,
        runtime_binary=runtime_binary,
        sandbox_policy=policy_value,
    )
    if policy is not None:
        validate_sandbox_workspace_toolchain(workspace_root)
    return sandbox_env, policy_value


__all__ = [
    "adapt_execution_policy",
    "prepare_execution_sandbox",
    "sandbox_agent_env",
]
