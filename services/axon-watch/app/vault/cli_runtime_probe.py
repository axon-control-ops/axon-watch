"""Lightweight CLI auth probes for vault consumer readiness (no secret values)."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from typing import Any

# Vault /status must stay under the console's 12s fetch budget. Cache CLI probes
# so hung `cursor`/`codex` status commands cannot keep Mission Control red.
_PROBE_CACHE_TTL_SECONDS = 90.0
_PROBE_TIMEOUT_SECONDS = 2
_probe_cache: dict[str, tuple[float, dict[str, Any]]] = {}


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


def _find_claude_cli() -> str:
    override = os.environ.get("AXON_WATCH_CLAUDE_CLI_PATH", "").strip()
    if _is_executable(override):
        return override
    for candidate in (
        shutil.which("claude") or "",
        os.path.expanduser("~/.local/bin/claude"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def _run_status(command: list[str], *, timeout: int = _PROBE_TIMEOUT_SECONDS) -> tuple[int, str]:
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


def _cached_probe(cache_key: str, builder) -> dict[str, Any]:
    now = time.monotonic()
    cached = _probe_cache.get(cache_key)
    if cached is not None:
        stamp, payload = cached
        if now - stamp < _PROBE_CACHE_TTL_SECONDS:
            return dict(payload)
    payload = builder()
    _probe_cache[cache_key] = (now, dict(payload))
    return dict(payload)


def clear_cli_runtime_probe_cache() -> None:
    _probe_cache.clear()


def probe_cursor_cli_subscription() -> dict[str, Any]:
    """Return subscription auth state from `cursor agent status` (per Cursor CLI docs)."""

    def _build() -> dict[str, Any]:
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
        if (
            returncode == 0
            and raw
            and "not logged in" not in lowered
            and "authentication required" not in lowered
        ):
            account = raw.splitlines()[0].strip()
            if account.startswith("✓"):
                account = account.lstrip("✓").strip()
            if account.lower().startswith("logged in as "):
                account = account[len("logged in as ") :].strip()
            return {
                "installed": True,
                "logged_in": True,
                "account_label": account,
                "message": (
                    f"Cursor CLI subscription ({account})"
                    if account
                    else "Cursor CLI subscription active."
                ),
            }
        return {
            "installed": True,
            "logged_in": False,
            "account_label": "",
            "message": "Run `cursor agent login` on the host or add CURSOR_API_KEY to /vault.",
        }

    return _cached_probe("cursor", _build)


def probe_codex_cli_subscription() -> dict[str, Any]:
    def _build() -> dict[str, Any]:
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

    return _cached_probe("codex", _build)


def probe_claude_cli_subscription() -> dict[str, Any]:
    def _build() -> dict[str, Any]:
        binary = _find_claude_cli()
        if not binary:
            return {
                "installed": False,
                "logged_in": False,
                "account_label": "",
                "message": "Claude Code CLI not installed on this host.",
            }
        returncode, raw = _run_status([binary, "auth", "status", "--json"])
        logged_in = False
        account = ""
        if returncode == 0 and raw:
            try:
                import json

                payload = json.loads(raw)
                if isinstance(payload, dict):
                    logged_in = bool(payload.get("loggedIn"))
                    account = str(payload.get("email") or payload.get("orgName") or "").strip()
            except Exception:
                logged_in = "logged in" in raw.lower()
                account = raw.splitlines()[0].strip() if raw else ""
        if logged_in:
            return {
                "installed": True,
                "logged_in": True,
                "account_label": account,
                "message": (
                    f"Claude Code subscription ({account})"
                    if account
                    else "Claude Code subscription active."
                ),
            }
        return {
            "installed": True,
            "logged_in": False,
            "account_label": "",
            "message": "Run `claude auth login` on the host or add ANTHROPIC_API_KEY to /vault.",
        }

    return _cached_probe("claude", _build)
