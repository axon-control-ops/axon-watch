"""Fail-closed Bubblewrap launcher and immutable per-run Cursor hook material."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from app.cli_runtime.agent_sandbox_paths import append_hidden_mounts, hidden_workspace_paths
from app.cli_runtime.user_bin_path import existing_user_local_bin, sandbox_path_with_user_bins

_SANDBOX_HOME = Path("/run/axon-agent-home")
_SANDBOX_POLICY_ROOT = Path("/run/axon-agent-policy")
_HOOK_TIMEOUT_SECONDS = 5
_SYSTEM_DIRS = ("/usr", "/bin", "/sbin", "/lib", "/lib64")
_SYSTEM_FILES = (
    "/etc/group", "/etc/hosts", "/etc/ld.so.cache", "/etc/localtime",
    "/etc/nsswitch.conf", "/etc/passwd", "/etc/resolv.conf",
)
_SYSTEM_CONFIG_DIRS = ("/etc/ssl", "/etc/ca-certificates")

class SandboxConfigurationError(RuntimeError):
    """Raised instead of running without a requested sandbox boundary."""


@dataclass(frozen=True)
class AgentSandboxPolicy:
    """Run-scoped inputs needed by the process and hook enforcement layers."""

    writable_roots: tuple[str, ...] = ()
    approved_wrappers: tuple[str, ...] = ()
    approved_command_prefixes: tuple[tuple[str, ...], ...] = ()
    cursor_readonly_paths: tuple[str, ...] = ()
    forbidden_path_globs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CursorHookMaterial:
    policy_id: str
    root: Path
    hooks_json: Path
    policy_json: Path
    hook_script: Path
    workspace_scratch: Path
    workspace_codex_scratch: Path


@dataclass(frozen=True)
class SandboxLaunch:
    command: tuple[str, ...]
    hook_material: CursorHookMaterial | None = None


def _canonical_json(document: object) -> bytes:
    return (
        json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _validate_policy(policy: AgentSandboxPolicy) -> None:
    for wrapper in policy.approved_wrappers:
        if (
            not wrapper
            or wrapper != os.path.basename(wrapper)
            or any(character.isspace() for character in wrapper)
            or "\x00" in wrapper
        ):
            raise SandboxConfigurationError(f"Invalid approved wrapper name: {wrapper!r}")
    for prefix in policy.approved_command_prefixes:
        if not prefix or any(not token or "\x00" in token for token in prefix):
            raise SandboxConfigurationError("Approved command prefixes must contain valid tokens.")


_ROLE_WRITE_SCOPE_HINTS: dict[str, list[str]] = {
    "frontend": [
        "app/",
        "apps/",
        "src/",
        "components/",
        "features/",
        "screens/",
        "hooks/",
        "locales/",
        "packages/",
        "tests/",
        "__tests__/",
    ],
    "backend": ["services/", "server/", "api/", "lib/", "supabase/", "packages/", "tests/"],
    "integrations": [".github/", "config/", "scripts/"],
    "lead": ["docs/planning/", "docs/ops/", "plans/"],
}


def _write_scope_specialist_hint(writable_roots: tuple[str, ...]) -> str:
    """Return a plain-language hint about which specialist role can write paths not in writable_roots."""
    if not writable_roots:
        return (
            "This agent role has read-only access to the workspace. "
            "To make code changes, dispatch a specialist: "
            "frontend (UI/screens/components/hooks), backend (services/api/lib), "
            "or integrations (scripts/config/.github)."
        )
    roots_str = ", ".join(sorted(writable_roots))
    return (
        f"This agent can only write within: {roots_str}. "
        "For paths outside this scope, dispatch the appropriate specialist: "
        "frontend (app/components/features/screens/hooks), "
        "backend (services/api/lib/supabase), "
        "integrations (scripts/config/.github). "
        "Do NOT ask the operator to remount the filesystem — use dispatch instead."
    )


def _policy_document(policy: AgentSandboxPolicy) -> dict[str, object]:
    _validate_policy(policy)
    return {
        "version": 1,
        "approved_wrappers": sorted(set(policy.approved_wrappers)),
        "approved_command_prefixes": [
            list(prefix) for prefix in policy.approved_command_prefixes
        ],
        "forbidden_path_globs": sorted(set(policy.forbidden_path_globs)),
        "writable_roots": sorted(set(policy.writable_roots)),
        "write_scope_hint": _write_scope_specialist_hint(policy.writable_roots),
    }


def _trusted_wrapper_sources(
    policy: AgentSandboxPolicy,
    workspace: Path,
) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for wrapper in policy.approved_wrappers:
        if wrapper == "axon-agent-terminal-job":
            # This capability is materialized from the running control-plane
            # package below. Never resolve a PATH entry for it: local installs
            # commonly symlink back into the workspace being sandboxed.
            continue
        installed = shutil.which(wrapper)
        if not installed:
            continue
        source = Path(installed).resolve(strict=True)
        if _is_relative_to(source, workspace):
            raise SandboxConfigurationError("Approved wrappers cannot come from the workspace.")
        sources[wrapper] = source
    return sources


def _builtin_wrapper_source(wrapper: str) -> bytes | None:
    if wrapper != "axon-agent-terminal-job":
        return None
    return Path(__file__).with_name("agent_terminal_job_wrapper.py").read_bytes()


def _prepare_workspace_scratch(workspace: Path, target: Path, name: str) -> None:
    """Reserve an empty mount point for agent-owned ephemeral state.

    Agent CLIs may create private state directories in their current project
    directory, including ``.agents`` and Codex's ``.codex``.
    The checkout itself is read-only inside Bubblewrap, so Bubblewrap attempts
    to create that destination and dies before the runtime can answer. We
    reserve only the empty host mount point, then bind a private per-run
    directory over it. Agent writes never land in the selected workspace or
    in a later commit.
    """
    destination = workspace / name
    if destination.exists():
        if destination.is_symlink() or not destination.is_dir():
            raise SandboxConfigurationError("Agent project scratch is not a safe directory.")
        if any(destination.iterdir()):
            raise SandboxConfigurationError("Agent project scratch must be empty before launch.")
    else:
        destination.mkdir(mode=0o700)
    if target.is_symlink() or not target.is_dir():
        raise SandboxConfigurationError("Private agent scratch is not a safe directory.")


def _hooks_document() -> dict[str, object]:
    hook_command = (
        f"/usr/bin/python3 {_SANDBOX_POLICY_ROOT}/hook.py "
        f"{_SANDBOX_POLICY_ROOT}/policy.json"
    )
    definition = {
        "command": hook_command,
        "failClosed": True,
        "timeout": _HOOK_TIMEOUT_SECONDS,
    }
    return {
        "version": 1,
        "hooks": {
            "beforeShellExecution": [definition],
            "preToolUse": [{**definition, "matcher": "Shell"}],
        },
    }


def default_policy_root() -> Path:
    runtime_root = Path(f"/run/user/{os.getuid()}")
    if runtime_root.is_dir():
        return runtime_root / "axon-watch" / "agent-sandbox-policies"
    return Path(tempfile.gettempdir()) / f"axon-watch-{os.getuid()}" / "agent-sandbox-policies"


def _write_immutable(path: Path, content: bytes, *, executable: bool = False) -> None:
    mode = 0o555 if executable else 0o444
    if path.exists():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != content:
            raise SandboxConfigurationError(
                f"Immutable sandbox policy collision at {path}."
            )
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


def materialize_cursor_hook_policy(
    *,
    policy: AgentSandboxPolicy,
    run_id: str,
    workspace_root: Path,
    policy_root: Path | None = None,
) -> CursorHookMaterial:
    """Create deterministic read-only hook files in host state, never the checkout."""
    cleaned_run_id = str(run_id or "").strip()
    if not cleaned_run_id:
        raise SandboxConfigurationError("A non-empty run_id is required for sandbox hooks.")

    workspace = workspace_root.resolve(strict=True)
    root = (policy_root or default_policy_root()).expanduser().resolve(strict=False)
    if _is_relative_to(root, workspace):
        raise SandboxConfigurationError("Sandbox hook policy root must be outside the workspace.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    root.chmod(0o700)

    policy_bytes = _canonical_json(_policy_document(policy))
    identity = hashlib.sha256(cleaned_run_id.encode("utf-8")).hexdigest()[:24]
    policy_id = f"run-{identity}"
    target = root / policy_id
    target.mkdir(mode=0o700, exist_ok=True)
    if target.is_symlink() or not target.is_dir():
        raise SandboxConfigurationError("Sandbox policy target is not a safe directory.")
    target.chmod(0o700)

    generated_home = target / "home"
    cursor_dir = generated_home / ".cursor"
    cursor_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if (
        generated_home.is_symlink()
        or cursor_dir.is_symlink()
        or not generated_home.is_dir()
        or not cursor_dir.is_dir()
    ):
        raise SandboxConfigurationError("Sandbox policy contains an unsafe directory.")

    hook_source = Path(__file__).with_name("agent_shell_hook.py").read_bytes()
    hooks_path = cursor_dir / "hooks.json"
    policy_path = target / "policy.json"
    hook_path = target / "hook.py"
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
        raise SandboxConfigurationError("Sandbox policy scratch contains an unsafe directory.")
    _write_immutable(hooks_path, _canonical_json(_hooks_document()))
    _write_immutable(policy_path, policy_bytes)
    _write_immutable(hook_path, hook_source, executable=True)
    for wrapper in policy.approved_wrappers:
        source = _builtin_wrapper_source(wrapper)
        if source is not None:
            _write_immutable(wrapper_dir / wrapper, source, executable=True)
    for wrapper, source in _trusted_wrapper_sources(policy, workspace).items():
        proxy = f"#!/bin/sh\nexec {shlex.quote(str(source))} \"$@\"\n".encode()
        _write_immutable(wrapper_dir / wrapper, proxy, executable=True)

    wrapper_dir.chmod(0o555)
    cursor_dir.chmod(0o555)
    generated_home.chmod(0o555)
    target.chmod(0o555)
    return CursorHookMaterial(
        policy_id=policy_id,
        root=target,
        hooks_json=hooks_path,
        policy_json=policy_path,
        hook_script=hook_path,
        workspace_scratch=workspace_scratch,
        workspace_codex_scratch=workspace_codex_scratch,
    )


def require_bubblewrap(bwrap_path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve an executable Bubblewrap binary or fail before process launch."""
    candidate = str(bwrap_path) if bwrap_path is not None else shutil.which("bwrap")
    if not candidate:
        raise SandboxConfigurationError(
            "Bubblewrap is required when an agent sandbox policy is supplied."
        )
    try:
        resolved = Path(candidate).resolve(strict=True)
    except OSError as exc:
        raise SandboxConfigurationError("Configured Bubblewrap binary does not exist.") from exc
    if not resolved.is_file() or not os.access(resolved, os.X_OK):
        raise SandboxConfigurationError("Configured Bubblewrap binary is not executable.")
    return resolved


def _resolve_workspace_root(workspace_root: Path) -> Path:
    try:
        workspace = workspace_root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise SandboxConfigurationError("Disposable workspace does not exist.") from exc
    if not workspace.is_dir():
        raise SandboxConfigurationError("Disposable workspace must be a directory.")
    return workspace


def _resolve_workspace_path(workspace: Path, configured: str) -> Path:
    raw = Path(configured).expanduser()
    candidate = raw if raw.is_absolute() else workspace / raw
    resolved = candidate.resolve(strict=False)
    if not _is_relative_to(resolved, workspace):
        raise SandboxConfigurationError(
            f"Approved writable root escapes the disposable workspace: {configured!r}"
        )
    # Writable roots are usually role-baseline directories (e.g. "docs/ops"),
    # but a leased task may narrow authority to one existing file. The latter
    # is safe to bind directly over the read-only workspace and must not be
    # rejected merely because it is not a directory.
    if resolved.exists() and resolved.is_file():
        return resolved
    # Role-baseline directories are applied across every workspace's
    # disposable checkout. Requiring one to pre-exist turned an approved,
    # boundary-checked target into a hard dispatch failure. Create a missing
    # directory instead — this narrows no existing authority.
    if not resolved.exists():
        try:
            resolved.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SandboxConfigurationError(
                f"Approved writable root does not exist and could not be created: {configured!r}"
            ) from exc
    elif not resolved.is_dir():
        raise SandboxConfigurationError(
            f"Approved writable root is not a directory: {configured!r}"
        )
    return resolved


def _resolve_cursor_path(path: str, *, user_home: Path, workspace: Path) -> Path:
    raw = Path(path).expanduser()
    candidate = raw if raw.is_absolute() else user_home / raw
    try:
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SandboxConfigurationError(
            f"Cursor runtime/config path does not exist: {path!r}"
        ) from exc
    if not _is_relative_to(resolved, user_home):
        raise SandboxConfigurationError(
            f"Cursor runtime/config path must stay within the user home: {path!r}"
        )
    if _is_relative_to(resolved, workspace) or _is_relative_to(workspace, resolved):
        raise SandboxConfigurationError("Cursor runtime/config mounts cannot overlap the workspace.")
    hooks_path = user_home / ".cursor" / "hooks.json"
    if resolved == user_home / ".cursor" or _is_relative_to(hooks_path, resolved):
        raise SandboxConfigurationError(
            "Cursor config mount would shadow the immutable per-run hooks."
        )
    return resolved


def _append_dirs(arguments: list[str], paths: Sequence[Path]) -> None:
    seen: set[str] = set()
    for path in paths:
        for parent in reversed(path.parents):
            if str(parent) in {".", "/"}:
                continue
            value = str(parent)
            if value not in seen:
                arguments.extend(["--dir", value])
                seen.add(value)


def build_bwrap_command(
    command: Sequence[str],
    *,
    policy: AgentSandboxPolicy,
    workspace_root: Path,
    hook_material: CursorHookMaterial,
    bwrap_path: str | os.PathLike[str] | None = None,
    user_home: Path | None = None,
) -> list[str]:
    """Build the Bubblewrap argv while validating every host path first."""
    cleaned = [str(part) for part in command if str(part)]
    if not cleaned:
        raise SandboxConfigurationError("Sandboxed command cannot be empty.")
    # The binary is commonly a symlink (npm/nvm-managed CLIs live several
    # hops deep, e.g. ~/.local/bin/cursor-agent -> .../versions/<ver>/cursor-agent).
    # cursor_readonly_paths below is computed by resolving that same chain
    # to its real target directory — if we exec the *unresolved* symlink
    # path instead, bwrap can't find it (it was never bind-mounted; only its
    # resolved target was), so every sandboxed run of a symlinked CLI failed
    # outright. Resolve here too so the exec target always matches what's
    # actually exposed to the sandbox.
    binary_path = Path(cleaned[0])
    if binary_path.is_symlink() or not binary_path.is_absolute():
        try:
            cleaned[0] = str(binary_path.resolve(strict=True))
        except OSError:
            pass
    _validate_policy(policy)
    bwrap = require_bubblewrap(bwrap_path)
    workspace = _resolve_workspace_root(workspace_root)
    home = (user_home or Path.home()).expanduser().resolve(strict=True)
    if not home.is_dir():
        raise SandboxConfigurationError("Sandbox user home must be a directory.")

    material_root = hook_material.root.resolve(strict=True)
    if _is_relative_to(material_root, workspace):
        raise SandboxConfigurationError("Sandbox hook material must remain outside the workspace.")
    for material_path in (
        hook_material.hooks_json,
        hook_material.policy_json,
        hook_material.hook_script,
    ):
        resolved_material_path = material_path.resolve(strict=True)
        if not _is_relative_to(resolved_material_path, material_root):
            raise SandboxConfigurationError("Sandbox hook material contains an escaped path.")
    workspace_scratch = hook_material.workspace_scratch.resolve(strict=True)
    workspace_codex_scratch = hook_material.workspace_codex_scratch.resolve(strict=True)
    if not _is_relative_to(workspace_scratch, material_root) or not _is_relative_to(
        workspace_codex_scratch, material_root
    ):
        raise SandboxConfigurationError("Sandbox scratch contains an escaped path.")
    _prepare_workspace_scratch(workspace, workspace_scratch, ".agents")
    _prepare_workspace_scratch(workspace, workspace_codex_scratch, ".codex")
    writable_roots = tuple(
        dict.fromkeys(_resolve_workspace_path(workspace, path) for path in policy.writable_roots)
    )
    hidden_paths = hidden_workspace_paths(workspace, policy.forbidden_path_globs)
    cursor_paths = tuple(
        dict.fromkeys(
            _resolve_cursor_path(path, user_home=home, workspace=workspace)
            for path in policy.cursor_readonly_paths
        )
    )
    wrapper_sources = tuple(_trusted_wrapper_sources(policy, workspace).values())
    cursor_paths = tuple(dict.fromkeys((*cursor_paths, *(
        source for source in wrapper_sources if _is_relative_to(source, home)
    ))))
    user_local_bin = existing_user_local_bin(home)

    arguments = [
        str(bwrap),
        "--die-with-parent",
        "--new-session",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--unshare-cgroup",
        "--cap-drop",
        "ALL",
    ]
    for system_dir in (*_SYSTEM_DIRS, *_SYSTEM_CONFIG_DIRS):
        source = Path(system_dir)
        if source.exists():
            arguments.extend(["--ro-bind", system_dir, system_dir])
    arguments.extend(["--dir", "/etc"])
    for system_file in _SYSTEM_FILES:
        source = Path(system_file)
        if source.exists():
            arguments.extend(["--ro-bind", system_file, system_file])
    arguments.extend(
        [
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
            "--tmpfs",
            "/var/tmp",
            "--tmpfs",
            "/run",
            "--tmpfs",
            "/home",
        ]
    )

    destination_paths = [workspace, _SANDBOX_HOME / ".cursor" / "hooks.json"]
    if user_local_bin is not None:
        destination_paths.append(user_local_bin)
    destination_paths.extend(cursor_paths)
    destination_paths.extend(
        _SANDBOX_HOME / path.relative_to(home) for path in cursor_paths
    )
    _append_dirs(arguments, destination_paths)

    arguments.extend(["--ro-bind", str(workspace), str(workspace)])
    for writable_root in writable_roots:
        arguments.extend(["--bind", str(writable_root), str(writable_root)])
    arguments.extend(["--bind", str(workspace_scratch), str(workspace / ".agents")])
    arguments.extend(["--bind", str(workspace_codex_scratch), str(workspace / ".codex")])
    append_hidden_mounts(arguments, hidden_paths)

    arguments.extend(
        [
            "--ro-bind",
            str(material_root),
            str(_SANDBOX_POLICY_ROOT),
            "--ro-bind",
            str(hook_material.hooks_json),
            str(_SANDBOX_HOME / ".cursor" / "hooks.json"),
        ]
    )
    for cursor_path in cursor_paths:
        arguments.extend(["--ro-bind", str(cursor_path), str(cursor_path)])
        home_destination = _SANDBOX_HOME / cursor_path.relative_to(home)
        arguments.extend(["--ro-bind", str(cursor_path), str(home_destination)])
    if user_local_bin is not None:
        arguments.extend(["--ro-bind", str(user_local_bin), str(user_local_bin)])

    arguments.extend(
        [
            "--setenv",
            "HOME",
            str(_SANDBOX_HOME),
            "--setenv",
            "PATH",
            sandbox_path_with_user_bins(user_local_bin),
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--chdir",
            str(workspace),
            "--",
            *cleaned,
        ]
    )
    return arguments


def wrap_command_in_agent_sandbox(
    command: Sequence[str],
    *,
    policy: AgentSandboxPolicy | None,
    workspace_root: Path,
    run_id: str,
    policy_root: Path | None = None,
    bwrap_path: str | os.PathLike[str] | None = None,
    user_home: Path | None = None,
) -> SandboxLaunch:
    """Generic opt-in wrapper; supplying policy can never silently run unsandboxed."""
    cleaned = tuple(str(part) for part in command if str(part))
    if policy is None:
        return SandboxLaunch(command=cleaned)

    # Check this first so a missing sandbox dependency cannot leave misleading policy state.
    resolved_bwrap = require_bubblewrap(bwrap_path)
    workspace = _resolve_workspace_root(workspace_root)
    material = materialize_cursor_hook_policy(
        policy=policy,
        run_id=run_id,
        workspace_root=workspace,
        policy_root=policy_root,
    )
    wrapped = build_bwrap_command(
        cleaned,
        policy=policy,
        workspace_root=workspace,
        hook_material=material,
        bwrap_path=resolved_bwrap,
        user_home=user_home,
    )
    return SandboxLaunch(command=tuple(wrapped), hook_material=material)


__all__ = [
    "AgentSandboxPolicy",
    "CursorHookMaterial",
    "SandboxConfigurationError",
    "SandboxLaunch",
    "build_bwrap_command",
    "default_policy_root",
    "materialize_cursor_hook_policy",
    "require_bubblewrap",
    "wrap_command_in_agent_sandbox",
]
