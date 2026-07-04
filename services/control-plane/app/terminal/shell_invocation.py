"""Deterministic shell invocation for workspace PTY sessions."""

from __future__ import annotations

import os
from pathlib import Path

_TERMINAL_DIR = Path(__file__).resolve().parent
_ZDOTDIR = _TERMINAL_DIR / "zdotdir"


def resolve_terminal_shell() -> str:
    return os.environ.get("AXON_WATCH_TERMINAL_SHELL", os.environ.get("SHELL", "/bin/bash"))


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


def build_shell_env(base_env: dict[str, str], *, workspace_root: str, shell: str) -> dict[str, str]:
    env = base_env.copy()
    env.setdefault("TERM", "xterm-256color")
    env.setdefault("COLORTERM", "truecolor")
    env["PWD"] = workspace_root
    env["STARSHIP_DISABLED"] = "1"
    env["DISABLE_AUTO_TITLE"] = "1"
    env["HISTFILE"] = str(Path(workspace_root) / ".axon_terminal_history")

    shell_name = Path(shell).name
    if shell_name == "zsh":
        env["ZDOTDIR"] = str(_ZDOTDIR)
        env["SAVEHIST"] = "5000"
        env["HISTSIZE"] = "5000"
    elif shell_name == "bash":
        env["HISTSIZE"] = "5000"
        env["HISTFILESIZE"] = "5000"

    return env
