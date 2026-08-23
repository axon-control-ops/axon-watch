"""Immutable per-run sandbox hook materialization helpers."""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from app.cli_runtime.agent_sandbox_hook_docs import _claude_settings_document, _hooks_document

_SANDBOX_GIT_ROOT = Path("/run/axon-agent-git")
CURSOR_WRITABLE_STATE_RELATIVE = (
    ".cursor/cli-config.json",
    ".cursor/agent-cli-state.json",
)


@dataclass(frozen=True)
class CursorHookMaterial:
    policy_id: str
    root: Path
    hooks_json: Path
    policy_json: Path
    hook_script: Path
    git_config: Path
    git_marker: Path | None
    workspace_scratch: Path
    workspace_codex_scratch: Path
    sandbox_home: Path


def default_policy_root() -> Path:
    runtime_root = Path(f"/run/user/{os.getuid()}")
    if runtime_root.is_dir():
        return runtime_root / "axon-watch" / "agent-sandbox-policies"
    return Path(tempfile.gettempdir()) / f"axon-watch-{os.getuid()}" / "agent-sandbox-policies"


def materialize_cursor_hook_policy(
    *,
    policy,
    run_id: str,
    workspace_root: Path,
    is_relative_to,
    linked_worktree_git_metadata,
    policy_document,
    policy_root: Path | None = None,
    user_home: Path | None = None,
    error_type: type[RuntimeError],
) -> CursorHookMaterial:
    """Create deterministic read-only hook files in host state, never the checkout."""
    cleaned_run_id = str(run_id or "").strip()
    if not cleaned_run_id:
        raise error_type("A non-empty run_id is required for sandbox hooks.")

    workspace = workspace_root.resolve(strict=True)
    root = (policy_root or default_policy_root()).expanduser().resolve(strict=False)
    if is_relative_to(root, workspace):
        raise error_type("Sandbox hook policy root must be outside the workspace.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)

    policy_bytes = _canonical_json(policy_document(policy))
    policy_id = f"run-{hashlib.sha256(cleaned_run_id.encode('utf-8')).hexdigest()[:24]}"
    target = root / policy_id
    target.mkdir(mode=0o700, exist_ok=True)
    if target.is_symlink() or not target.is_dir():
        raise error_type("Sandbox policy target is not a safe directory.")
    target.chmod(0o700)

    generated_home = target / "home"
    cursor_dir = generated_home / ".cursor"
    cursor_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if user_home is not None:
        _seed_cursor_writable_state(user_home=user_home.expanduser().resolve(), cursor_dir=cursor_dir)
    if (
        generated_home.is_symlink()
        or cursor_dir.is_symlink()
        or not generated_home.is_dir()
        or not cursor_dir.is_dir()
    ):
        raise error_type("Sandbox policy contains an unsafe directory.")

    hook_source = Path(__file__).with_name("agent_shell_hook.py").read_bytes()
    hooks_path = cursor_dir / "hooks.json"
    policy_path = target / "policy.json"
    hook_path = target / "hook.py"
    git_config_path = target / "gitconfig"
    linked_git = linked_worktree_git_metadata(workspace)
    git_marker_path = target / "git-worktree"
    wrapper_dir = target / "bin"
    scratch_root = target / "scratch"
    workspace_scratch = scratch_root / ".agents"
    workspace_codex_scratch = scratch_root / ".codex"
    wrapper_dir.mkdir(mode=0o700, exist_ok=True)
    workspace_scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    workspace_codex_scratch.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        scratch_root.is_symlink()
        or workspace_scratch.is_symlink()
        or workspace_codex_scratch.is_symlink()
    ):
        raise error_type("Sandbox policy scratch contains an unsafe directory.")
    claude_dir = generated_home / ".claude"
    claude_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if claude_dir.is_symlink() or not claude_dir.is_dir():
        raise error_type("Sandbox policy contains an unsafe directory.")
    try:
        _write_immutable(hooks_path, _canonical_json(_hooks_document()))
        _write_immutable(
            claude_dir / "settings.json",
            _canonical_json(_claude_settings_document()),
        )
        _write_immutable(policy_path, policy_bytes)
        _write_immutable(hook_path, hook_source, executable=True)
        _write_immutable(git_config_path, b"")
        if linked_git is not None:
            _common_git_dir, worktree_relative = linked_git
            sandbox_git_dir = _SANDBOX_GIT_ROOT / "common" / worktree_relative
            _write_immutable(git_marker_path, f"gitdir: {sandbox_git_dir}\n".encode("utf-8"))
        for wrapper in policy.approved_wrappers:
            source = _builtin_wrapper_source(wrapper)
            if source is not None:
                _write_immutable(wrapper_dir / wrapper, source, executable=True)
        for wrapper, source in _trusted_wrapper_sources(
            policy, workspace, is_relative_to, error_type
        ).items():
            proxy = f"#!/bin/sh\nexec {shlex.quote(str(source))} \"$@\"\n".encode()
            _write_immutable(wrapper_dir / wrapper, proxy, executable=True)
    except ValueError as exc:
        raise error_type(str(exc)) from exc

    wrapper_dir.chmod(0o555)
    claude_dir.chmod(0o700)
    cursor_dir.chmod(0o700)
    generated_home.chmod(0o700)
    target.chmod(0o555)
    return CursorHookMaterial(
        policy_id=policy_id,
        root=target,
        hooks_json=hooks_path,
        policy_json=policy_path,
        hook_script=hook_path,
        git_config=git_config_path,
        git_marker=git_marker_path if linked_git is not None else None,
        workspace_scratch=workspace_scratch,
        workspace_codex_scratch=workspace_codex_scratch,
        sandbox_home=generated_home,
    )


def _canonical_json(document: object) -> bytes:
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _builtin_wrapper_source(wrapper: str) -> bytes | None:
    if wrapper == "axon-agent-terminal-job":
        return Path(__file__).with_name("agent_terminal_job_wrapper.py").read_bytes()
    if wrapper == "axon-assign":
        return Path(__file__).with_name("agent_assign_wrapper.sh").read_bytes()
    if wrapper == "axon-runlog":
        return Path(__file__).with_name("agent_runlog_wrapper.sh").read_bytes()
    if wrapper == "axonhealth":
        return _AXONHEALTH_WRAPPER
    return None


_AXONHEALTH_WRAPPER = b"""#!/usr/bin/env bash
set -euo pipefail

: "${AXON_WATCH_CONSOLE_WEB_PORT:=4173}"
: "${AXON_WATCH_CONTROL_PLANE_PORT:=8787}"
: "${AXON_WATCH_WATCH_SERVICE_PORT:=8788}"

failures=0

probe() {
  local label="$1"
  local url="$2"
  local code
  code="$(curl -sS --max-time 8 -o /dev/null -w '%{http_code}' "${url}" 2>/dev/null || printf '000')"
  if [[ "${code}" == "200" ]]; then
    printf 'ok  %s  %s\\n' "${label}" "${url}"
  else
    printf 'FAIL %s  %s  (http %s)\\n' "${label}" "${url}" "${code}"
    failures=$((failures + 1))
  fi
}

echo "=== Axon-X sandbox health ==="
probe "console-web" "http://127.0.0.1:${AXON_WATCH_CONSOLE_WEB_PORT}/"
probe "control-plane health" "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/health"
probe "control-plane readiness" "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/readiness"
probe "watch health" "http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}/internal/watch/health"
probe "watch readiness" "http://127.0.0.1:${AXON_WATCH_WATCH_SERVICE_PORT}/internal/watch/readiness"
probe "runtime summary" "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/runtime/summary"
probe "inbox" "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/inbox"
probe "runs" "http://127.0.0.1:${AXON_WATCH_CONTROL_PLANE_PORT}/api/runs"

if (( failures > 0 )); then
  echo "Health FAILED (${failures} check(s))."
  exit 1
fi

echo "Health OK."
"""


def _seed_cursor_writable_state(*, user_home: Path, cursor_dir: Path) -> None:
    """Copy host Cursor state into the per-run sandbox HOME as writable files."""
    for relative in CURSOR_WRITABLE_STATE_RELATIVE:
        source = user_home / relative
        if not source.is_file():
            continue
        destination = cursor_dir / Path(relative).name
        if destination.exists():
            continue
        shutil.copy2(source, destination)
        destination.chmod(0o600)


def _trusted_wrapper_sources(
    policy, workspace: Path, is_relative_to, error_type: type[RuntimeError]
) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for wrapper in policy.approved_wrappers:
        if wrapper in {"axon-agent-terminal-job", "axon-assign", "axon-runlog", "axonhealth"}:
            continue
        installed = shutil.which(wrapper)
        if not installed:
            continue
        source = Path(installed).resolve(strict=True)
        if is_relative_to(source, workspace):
            raise error_type("Approved wrappers cannot come from the workspace.")
        sources[wrapper] = source
    return sources


def _write_immutable(path: Path, content: bytes, *, executable: bool = False) -> None:
    mode = 0o555 if executable else 0o444
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise ValueError(f"Immutable sandbox policy collision at {path}.")
        path.chmod(mode)
        return
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise
    path.chmod(mode)
