"""Fail-closed Bubblewrap launcher and immutable per-run Cursor hook material."""
from __future__ import annotations

import hashlib
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from app.cli_runtime.agent_sandbox_paths import (
    append_hidden_mounts,
    append_outside_symlink_binds,
    hidden_workspace_paths,
)
from app.cli_runtime.agent_sandbox_material import (
    CURSOR_WRITABLE_STATE_RELATIVE,
    CursorHookMaterial,
    default_policy_root,
    materialize_cursor_hook_policy as _materialize_cursor_hook_policy,
)
from app.cli_runtime.codex_profile_mount import append_codex_auth_mount, resolve_codex_auth_path
from app.cli_runtime.user_bin_path import existing_user_local_bin, sandbox_path_with_user_bins

_SANDBOX_HOME = Path("/run/axon-agent-home")
_SANDBOX_POLICY_ROOT = Path("/run/axon-agent-policy")
_SANDBOX_GIT_ROOT = Path("/run/axon-agent-git")
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
    # Codex can use an Axon-X profile outside the desktop user's home.  Its
    # auth file is mounted only at the sandbox's private CODEX_HOME.
    codex_auth_path: str = ""
    forbidden_path_globs: tuple[str, ...] = ()
    # Whitelisted service-bridge keys materialized with --setenv (never logged).
    injected_env: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class SandboxLaunch:
    command: tuple[str, ...]
    hook_material: CursorHookMaterial | None = None


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
        if wrapper in _BUILTIN_MATERIALIZED_WRAPPERS:
            # These capabilities are materialized from the running control-plane
            # package below. Never resolve a PATH entry for them: local installs
            # commonly symlink back into the repo checkout or the workspace
            # being sandboxed, and that source path is never bind-mounted, so
            # the resolved symlink is dangling inside Bubblewrap and the shell
            # reports the wrapper as "not found" even though it is genuinely
            # installed on the host.
            continue
        installed = shutil.which(wrapper)
        if not installed:
            continue
        source = Path(installed).resolve(strict=True)
        if _is_relative_to(source, workspace):
            raise SandboxConfigurationError("Approved wrappers cannot come from the workspace.")
        sources[wrapper] = source
    return sources
_BUILTIN_MATERIALIZED_WRAPPERS = frozenset(
    {"axon-agent-terminal-job", "axon-assign", "axon-runlog", "axonhealth"}
)
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


def materialize_cursor_hook_policy(
    *,
    policy: AgentSandboxPolicy,
    run_id: str,
    workspace_root: Path,
    policy_root: Path | None = None,
    user_home: Path | None = None,
) -> CursorHookMaterial:
    return _materialize_cursor_hook_policy(
        policy=policy,
        run_id=run_id,
        workspace_root=workspace_root,
        is_relative_to=_is_relative_to,
        linked_worktree_git_metadata=_linked_worktree_git_metadata,
        policy_document=_policy_document,
        policy_root=policy_root,
        user_home=user_home,
        error_type=SandboxConfigurationError,
    )


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


def _linked_worktree_git_metadata(workspace: Path) -> tuple[Path, Path] | None:
    """Return trusted external metadata for a disposable linked worktree.

    Composer and worker isolation roots are created with ``git worktree``.
    Their ``.git`` marker points back to the source repository, which is not
    otherwise visible inside Bubblewrap. Expose that metadata read-only so
    approved introspection such as ``git status`` works without allowing the
    runtime to mutate refs, config, hooks, or another worktree.
    """
    marker = workspace / ".git"
    if not marker.is_file() or marker.is_symlink():
        return None
    try:
        marker_text = marker.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    first_line = marker_text.splitlines()[0].strip() if marker_text else ""
    if not first_line.startswith("gitdir:"):
        return None
    raw_git_dir = first_line.removeprefix("gitdir:").strip()
    if not raw_git_dir:
        return None
    candidate = Path(raw_git_dir)
    if not candidate.is_absolute():
        candidate = marker.parent / candidate
    try:
        worktree_git_dir = candidate.resolve(strict=True)
        common_marker = worktree_git_dir / "commondir"
        raw_common = common_marker.read_text(encoding="utf-8").strip()
        common_git_dir = (worktree_git_dir / raw_common).resolve(strict=True)
    except (OSError, UnicodeError):
        return None
    if (
        common_git_dir.name != ".git"
        or not common_git_dir.is_dir()
        or not _is_relative_to(worktree_git_dir, common_git_dir / "worktrees")
        or _is_relative_to(common_git_dir, workspace)
    ):
        return None
    return common_git_dir, worktree_git_dir.relative_to(common_git_dir)


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
    material_paths = [
        hook_material.hooks_json,
        hook_material.policy_json,
        hook_material.hook_script,
        hook_material.git_config,
    ]
    if hook_material.git_marker is not None:
        material_paths.append(hook_material.git_marker)
    for material_path in material_paths:
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
    linked_git_metadata = _linked_worktree_git_metadata(workspace)
    common_git_dir = linked_git_metadata[0] if linked_git_metadata is not None else None
    if common_git_dir is not None and hook_material.git_marker is not None:
        hidden_paths = tuple(path for path in hidden_paths if path != workspace / ".git")
    cursor_paths = tuple(
        dict.fromkeys(
            _resolve_cursor_path(path, user_home=home, workspace=workspace)
            for path in policy.cursor_readonly_paths
        )
    )
    try:
        codex_auth_path = resolve_codex_auth_path(policy.codex_auth_path, workspace=workspace)
    except ValueError as exc:
        raise SandboxConfigurationError(str(exc)) from exc
    wrapper_sources = tuple(_trusted_wrapper_sources(policy, workspace).values())
    cursor_paths = tuple(dict.fromkeys((*cursor_paths, *(source for source in wrapper_sources if _is_relative_to(source, home)))))
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

    destination_paths = [
        workspace,
        _SANDBOX_HOME / ".cursor" / "hooks.json",
        _SANDBOX_HOME / ".claude" / "settings.json",
        _SANDBOX_HOME / ".codex" / "auth.json",
    ]
    if common_git_dir is not None and hook_material.git_marker is not None:
        destination_paths.append(_SANDBOX_GIT_ROOT / "common")
    if user_local_bin is not None:
        destination_paths.append(user_local_bin)
    destination_paths.extend(cursor_paths)
    destination_paths.extend(
        _SANDBOX_HOME / path.relative_to(home) for path in cursor_paths
    )
    _append_dirs(arguments, destination_paths)

    arguments.extend(["--ro-bind", str(workspace), str(workspace)])
    append_outside_symlink_binds(arguments, workspace)
    for writable_root in writable_roots:
        arguments.extend(["--bind", str(writable_root), str(writable_root)])
    if common_git_dir is not None and hook_material.git_marker is not None:
        # Keep both the pointer and all shared repository metadata immutable.
        # Mask repository config as well: status/diff need metadata, not remote
        # URLs or credentials that may have been embedded in local config.
        sandbox_common_git_dir = _SANDBOX_GIT_ROOT / "common"
        arguments.extend(["--ro-bind", str(common_git_dir), str(sandbox_common_git_dir)])
        arguments.extend(["--ro-bind", str(hook_material.git_marker), str(workspace / ".git")])
        for config_name in ("config", "config.worktree"):
            config_path = common_git_dir / config_name
            if config_path.is_file():
                arguments.extend([
                    "--ro-bind",
                    str(hook_material.git_config),
                    str(sandbox_common_git_dir / config_name),
                ])
    arguments.extend(["--bind", str(workspace_scratch), str(workspace / ".agents")])
    arguments.extend(["--bind", str(workspace_codex_scratch), str(workspace / ".codex")])
    append_hidden_mounts(arguments, hidden_paths)

    arguments.extend(
        [
            "--ro-bind",
            str(material_root),
            str(_SANDBOX_POLICY_ROOT),
        ]
    )
    sandbox_home = hook_material.sandbox_home.resolve(strict=True)
    arguments.extend(["--bind", str(sandbox_home), str(_SANDBOX_HOME)])
    arguments.extend(
        [
            "--ro-bind",
            str(hook_material.hooks_json),
            str(_SANDBOX_HOME / ".cursor" / "hooks.json"),
        ]
    )
    for cursor_path in cursor_paths:
        arguments.extend(["--ro-bind", str(cursor_path), str(cursor_path)])
        home_destination = _SANDBOX_HOME / cursor_path.relative_to(home)
        arguments.extend(["--ro-bind", str(cursor_path), str(home_destination)])
    append_codex_auth_mount(arguments, codex_auth_path, _SANDBOX_HOME / ".codex" / "auth.json")
    if user_local_bin is not None:
        arguments.extend(["--ro-bind", str(user_local_bin), str(user_local_bin)])

    for key, value in policy.injected_env:
        clean_key = str(key).strip()
        clean_value = str(value)
        if not clean_key or "\x00" in clean_key or "\x00" in clean_value:
            continue
        arguments.extend(["--setenv", clean_key, clean_value])
    arguments.extend(
        [
            "--setenv",
            "HOME",
            str(_SANDBOX_HOME),
            "--setenv",
            "PATH",
            sandbox_path_with_user_bins(user_local_bin, workspace=workspace),
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
        user_home=user_home,
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


__all__ = ["AgentSandboxPolicy", "CURSOR_WRITABLE_STATE_RELATIVE", "CursorHookMaterial", "SandboxConfigurationError",
           "SandboxLaunch", "build_bwrap_command", "default_policy_root",
           "materialize_cursor_hook_policy", "require_bubblewrap",
           "wrap_command_in_agent_sandbox"]
