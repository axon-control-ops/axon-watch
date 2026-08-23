"""Deterministic shell invocation for workspace PTY sessions."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from app.cli_runtime.user_bin_path import runtime_path_with_user_bins

_TERMINAL_DIR = Path(__file__).resolve().parent
_ZDOTDIR = _TERMINAL_DIR / "zdotdir"


def resolve_terminal_shell(preferred: str | None = None) -> str:
    """Pick an executable shell; prefer session title (zsh/bash), then env, then zsh."""
    preferred_name = Path(str(preferred or "").strip()).name.lower()
    if preferred_name in {"zsh", "bash"}:
        for candidate in (f"/bin/{preferred_name}", f"/usr/bin/{preferred_name}"):
            if Path(candidate).is_file():
                return candidate
        which = shutil.which(preferred_name)
        if which:
            return which
    env_shell = os.environ.get("AXON_WATCH_TERMINAL_SHELL") or os.environ.get("SHELL") or ""
    if env_shell and Path(env_shell).is_file():
        return env_shell
    for fallback in ("/bin/zsh", "/usr/bin/zsh", "/bin/bash", "/usr/bin/bash"):
        if Path(fallback).is_file():
            return fallback
    return env_shell or "/bin/zsh"


def bundled_bash_rc_path() -> Path:
    return _TERMINAL_DIR / "shell_bashrc.sh"


def zdotdir_path() -> Path:
    return _ZDOTDIR


def build_shell_command(shell: str) -> list[str]:
    shell_name = Path(shell).name
    if shell_name == "bash":
        return [shell, "--rcfile", str(bundled_bash_rc_path()), "-i"]
    if shell_name == "zsh":
        # zsh has no --rcfile; use ZDOTDIR with bundled .zshrc instead.
        return [shell, "-i"]
    return [shell, "-i"]


def build_shell_env(
    base_env: dict[str, str],
    *,
    workspace_root: str,
    shell: str,
    session_id: str | None = None,
) -> dict[str, str]:
    env = base_env.copy()
    env["PATH"] = runtime_path_with_user_bins(env.get("PATH", ""))
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("COLORTERM", "truecolor")
    env["PWD"] = workspace_root
    env["STARSHIP_DISABLED"] = "1"
    env["DISABLE_AUTO_TITLE"] = "1"
    session_suffix = f"_{session_id}" if str(session_id or "").strip() else ""
    env["HISTFILE"] = str(Path(workspace_root) / f".axon_terminal_history{session_suffix}")

    shell_name = Path(shell).name
    if shell_name == "zsh":
        env["ZDOTDIR"] = str(_ZDOTDIR)
        env["SAVEHIST"] = "5000"
        env["HISTSIZE"] = "5000"
    elif shell_name == "bash":
        env["HISTSIZE"] = "5000"
        env["HISTFILESIZE"] = "5000"

    return env
