"""CLI runtime login/logout actions for operator settings."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from app.cli_runtime.catalog import (
    find_codex_cli,
    find_cursor_cli,
    invalidate_runtime_snapshot_cache,
    runtime_status_snapshot,
)
from app.cli_runtime.cursor_models import cursor_runtime_snapshot

StatusRecord = dict[str, Any]


def _runtime_target(family: str) -> dict[str, Any] | None:
    snapshot = runtime_status_snapshot(force_refresh=True)
    for record in [*snapshot.get("local", []), *snapshot.get("cloud", [])]:
        if str(record.get("family", "")).strip() == family:
            return record
    return None


def _action_result(
    *,
    status: str,
    message: str,
    command_preview: str = "",
    output: str = "",
) -> StatusRecord:
    snapshot = runtime_status_snapshot(force_refresh=True)
    cursor = cursor_runtime_snapshot(force_refresh=True)
    return {
        "status": status,
        "message": message,
        "command_preview": command_preview,
        "output": output,
        "runtime_status": snapshot,
        "cursor_runtime": cursor,
    }


def logout_cursor_runtime() -> StatusRecord:
    binary = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
    target = _runtime_target("cursor")
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Cursor CLI is not installed on this host.",
        )
    if auth.get("auth_method") in {"api_key", "vault_api_key"}:
        return _action_result(
            status="manual_required",
            message="Cursor is authenticated via API key. Remove CURSOR_API_KEY from /vault or the shell env to sign out.",
            command_preview=f"{binary} agent status",
        )
    if not auth.get("logged_in"):
        return _action_result(
            status="completed",
            message="Cursor CLI is already signed out.",
            command_preview=f"{binary} agent status",
        )
    try:
        proc = subprocess.run(
            [binary, "agent", "logout"],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return _action_result(
            status="error",
            message="Cursor sign-out timed out. Run `cursor agent logout` on the host.",
            command_preview=f"{binary} agent logout",
        )
    output = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        return _action_result(
            status="error",
            message=output or "Cursor sign-out failed.",
            command_preview=f"{binary} agent logout",
            output=output,
        )
    invalidate_runtime_snapshot_cache()
    refreshed = _runtime_target("cursor")
    if bool(dict((refreshed or {}).get("auth") or {}).get("logged_in")):
        return _action_result(
            status="error",
            message="Cursor sign-out did not clear authentication.",
            command_preview=f"{binary} agent status",
            output=output,
        )
    return _action_result(
        status="completed",
        message="Cursor CLI signed out.",
        command_preview=f"{binary} agent status",
        output=output,
    )


def logout_codex_runtime() -> StatusRecord:
    binary = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())
    target = _runtime_target("codex")
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Codex CLI is not installed on this host.",
        )
    if auth.get("auth_method") in {"api_key", "vault_api_key"}:
        return _action_result(
            status="manual_required",
            message="Codex is authenticated via API key. Remove Codex/OpenAI keys from /vault or the shell env to sign out.",
            command_preview=f"{binary} login status",
        )
    if not auth.get("logged_in"):
        return _action_result(
            status="completed",
            message="Codex CLI is already signed out.",
            command_preview=f"{binary} login status",
        )
    try:
        proc = subprocess.run(
            [binary, "logout"],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return _action_result(
            status="error",
            message="Codex sign-out timed out. Run `codex logout` on the host.",
            command_preview=f"{binary} logout",
        )
    output = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        return _action_result(
            status="error",
            message=output or "Codex sign-out failed.",
            command_preview=f"{binary} logout",
            output=output,
        )
    invalidate_runtime_snapshot_cache()
    refreshed = _runtime_target("codex")
    if bool(dict((refreshed or {}).get("auth") or {}).get("logged_in")):
        return _action_result(
            status="error",
            message="Codex sign-out did not clear authentication.",
            command_preview=f"{binary} login status",
            output=output,
        )
    return _action_result(
        status="completed",
        message="Codex CLI signed out.",
        command_preview=f"{binary} login status",
        output=output,
    )


def start_cursor_runtime_login() -> StatusRecord:
    binary = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
    target = _runtime_target("cursor")
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Install Cursor CLI before signing in.",
        )
    if auth.get("logged_in") and auth.get("auth_method") == "oauth":
        account = str(auth.get("account_label") or "").strip()
        return _action_result(
            status="completed",
            message=f"Cursor CLI is already signed in{(': ' + account) if account else ''}.",
            command_preview=f"{binary} agent status",
        )
    command = [binary, "agent", "login"]
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except OSError as exc:
        return _action_result(
            status="manual_required",
            message=f"Could not start Cursor login on this host: {exc}. Run `{' '.join(command)}` in a terminal.",
            command_preview=" ".join(command),
        )
    return _action_result(
        status="browser_opened",
        message="Cursor login started — complete the browser flow on this host, then refresh status.",
        command_preview=" ".join(command),
    )


def start_codex_runtime_login() -> StatusRecord:
    binary = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())
    target = _runtime_target("codex")
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Install Codex CLI before signing in.",
        )
    if auth.get("logged_in") and auth.get("auth_method") in {"oauth", "chatgpt"}:
        account = str(auth.get("account_label") or "").strip()
        return _action_result(
            status="completed",
            message=f"Codex CLI is already signed in{(': ' + account) if account else ''}.",
            command_preview=f"{binary} login status",
        )
    command = [binary, "login"]
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except OSError as exc:
        return _action_result(
            status="manual_required",
            message=f"Could not start Codex login on this host: {exc}. Run `{' '.join(command)}` in a terminal.",
            command_preview=" ".join(command),
        )
    return _action_result(
        status="browser_opened",
        message="Codex login started — complete the browser flow on this host, then refresh status.",
        command_preview=" ".join(command),
    )
