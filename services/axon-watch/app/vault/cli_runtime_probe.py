"""Lightweight CLI auth probes for vault consumer readiness (no secret values)."""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def _find_cursor_cli() -> str:
    override = os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip()
    if _is_executable(override):
        return override
    for candidate in (
        shutil.which("cursor") or "",
        os.path.expanduser("~/.local/bin/cursor"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def _find_codex_cli() -> str:
    override = os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip()
    if _is_executable(override):
        return override
    for candidate in (
        shutil.which("codex") or "",
        os.path.expanduser("~/.local/bin/codex"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def _run_status(command: list[str], *, timeout: int = 8) -> tuple[int, str]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={**os.environ, "NO_COLOR": "1"},
        )
        return int(proc.returncode or 0), (proc.stdout or proc.stderr or "").strip()
    except (subprocess.TimeoutExpired, OSError):
        return 1, ""


def probe_cursor_cli_subscription() -> dict[str, Any]:
    """Return subscription auth state from `cursor agent status` (per Cursor CLI docs)."""
    binary = _find_cursor_cli()
    if not binary:
        return {
            "installed": False,
            "logged_in": False,
            "account_label": "",
            "message": "Cursor CLI not installed on this host.",
        }
    returncode, raw = _run_status([binary, "agent", "status"])
    lowered = raw.lower()
    if returncode == 0 and raw and "not logged in" not in lowered and "authentication required" not in lowered:
        account = raw.splitlines()[0].strip()
        if account.startswith("✓"):
            account = account.lstrip("✓").strip()
        if account.lower().startswith("logged in as "):
            account = account[len("logged in as ") :].strip()
        return {
            "installed": True,
            "logged_in": True,
            "account_label": account,
            "message": f"Cursor CLI subscription ({account})" if account else "Cursor CLI subscription active.",
        }
    return {
        "installed": True,
        "logged_in": False,
        "account_label": "",
        "message": "Run `cursor agent login` on the host or add CURSOR_API_KEY to /vault.",
    }


def probe_codex_cli_subscription() -> dict[str, Any]:
    binary = _find_codex_cli()
    if not binary:
        return {
            "installed": False,
            "logged_in": False,
            "account_label": "",
            "message": "Codex CLI not installed on this host.",
        }
    returncode, raw = _run_status([binary, "login", "status"])
    if returncode == 0 and raw:
        account = raw.splitlines()[0].strip()
        return {
            "installed": True,
            "logged_in": True,
            "account_label": account,
            "message": "Codex CLI signed in.",
        }
    return {
        "installed": True,
        "logged_in": False,
        "account_label": "",
        "message": "Run `codex login` on the host or add CODEX/OPENAI keys to /vault.",
    }
