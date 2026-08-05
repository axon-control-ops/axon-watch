"""Local CLI binary discovery shared by runtime catalog consumers."""

from __future__ import annotations

import os
import shutil


def cli_runtime_family(path: str = "") -> str:
    candidate = os.path.basename(str(path or "")).strip().lower()
    if candidate in {"cursor", "cursor-agent"}:
        return "cursor"
    if candidate in {"claude", "claude-code"} or candidate.startswith("claude"):
        return "claude"
    if "codex" in candidate:
        return "codex"
    return ""


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _find_cli(override_path: str, family: str, candidates: tuple[str, ...]) -> str:
    if _is_executable(override_path) and cli_runtime_family(override_path) == family:
        return override_path
    for candidate in candidates:
        if _is_executable(candidate) and cli_runtime_family(candidate) == family:
            return candidate
    return ""


def find_cursor_cli(override_path: str = "") -> str:
    # Prefer the "cursor-agent" binary over the "cursor" IDE-launcher shim:
    # the shim's own dispatch logic re-execs through a *separate* "agent"
    # symlink at runtime (`exec "$HOME/.local/bin/agent" "$@"`), which our
    # process sandbox has no way to see — it only bind-mounts the resolved
    # binary's own directory, not a second hop the binary jumps to on its
    # own. That left every sandboxed Cursor dispatch running the shim
    # against a symlink target that was never exposed to the sandbox,
    # surfacing as a spurious "Could not install cursor-agent" failure.
    # cursor-agent has no such indirection, so resolving straight to it
    # keeps sandbox path resolution and actual execution in agreement.
    return _find_cli(
        override_path,
        "cursor",
        (
            shutil.which("cursor-agent") or "",
            os.path.expanduser("~/.local/bin/cursor-agent"),
            os.path.expanduser("~/bin/cursor-agent"),
            shutil.which("cursor") or "",
            os.path.expanduser("~/.local/bin/cursor"),
            os.path.expanduser("~/bin/cursor"),
        ),
    )


def find_codex_cli(override_path: str = "") -> str:
    return _find_cli(
        override_path,
        "codex",
        (
            shutil.which("codex") or "",
            os.path.expanduser("~/.local/bin/codex"),
            os.path.expanduser("~/bin/codex"),
            os.path.expanduser("~/.npm-global/bin/codex"),
            os.path.expanduser("~/.volta/bin/codex"),
        ),
    )


def find_claude_cli(override_path: str = "") -> str:
    return _find_cli(
        override_path,
        "claude",
        (
            shutil.which("claude") or "",
            os.path.expanduser("~/.local/bin/claude"),
            os.path.expanduser("~/bin/claude"),
            os.path.expanduser("~/.npm-global/bin/claude"),
            os.path.expanduser("~/.volta/bin/claude"),
        ),
    )
