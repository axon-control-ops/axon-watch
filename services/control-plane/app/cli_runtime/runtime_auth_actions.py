"""CLI runtime login/logout actions for operator settings."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from app.cli_runtime.catalog import (
    find_claude_cli,
    find_codex_cli,
    find_cursor_cli,
    invalidate_runtime_snapshot_cache,
    runtime_status_snapshot,
)
from app.cli_runtime.catalog_discovery import cursor_cli_argv
from app.cli_runtime.cursor_models import cursor_runtime_snapshot
from app.cli_runtime.runtime_profiles import codex_profile_env

StatusRecord = dict[str, Any]


def _runtime_target(family: str, *, force_refresh: bool = False) -> dict[str, Any] | None:
    snapshot = runtime_status_snapshot(force_refresh=force_refresh)
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
    account_scope_notice: str = "",
    force_refresh: bool = True,
) -> StatusRecord:
    # Login start should return quickly so the browser flow can open; callers
    # refresh status after the operator completes auth.
    snapshot = runtime_status_snapshot(force_refresh=force_refresh)
    cursor = cursor_runtime_snapshot(force_refresh=force_refresh)
    return {
        "status": status,
        "message": message,
        "command_preview": command_preview,
        "output": output,
        "account_scope_notice": account_scope_notice,
        "runtime_status": snapshot,
        "cursor_runtime": cursor,
    }


def _host_cli_oauth_notice(runtime_label: str) -> str:
    return (
        f"{runtime_label} browser login is host-profile scoped. If another account is "
        "already active in this machine session, sign out first or use Vault/API-key "
        "auth for the second account where that runtime supports it; Axon-X will not "
        "silently replace accounts."
    )


def logout_cursor_runtime() -> StatusRecord:
    binary = find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip())
    target = _runtime_target("cursor", force_refresh=False)
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
            command_preview=" ".join(cursor_cli_argv(binary, "status")),
        )
    if auth.get("auth_method") == "oauth":
        notice = _host_cli_oauth_notice("Cursor CLI")
        return _action_result(
            status="manual_required",
            message=(
                "Cursor CLI sign-out is host-profile scoped, so Axon-X will not run "
                "`cursor agent logout` from the console. Run it manually only if you "
                "intend to sign this host profile out of Cursor."
            ),
            command_preview=" ".join(cursor_cli_argv(binary, "logout")),
            account_scope_notice=notice,
            force_refresh=False,
        )
    if not auth.get("logged_in"):
        return _action_result(
            status="completed",
            message="Cursor CLI is already signed out.",
            command_preview=" ".join(cursor_cli_argv(binary, "status")),
        )
    logout_argv = cursor_cli_argv(binary, "logout")
    try:
        proc = subprocess.run(
            logout_argv,
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return _action_result(
            status="error",
            message=f"Cursor sign-out timed out. Run `{' '.join(logout_argv)}` on the host.",
            command_preview=" ".join(logout_argv),
        )
    output = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        return _action_result(
            status="error",
            message=output or "Cursor sign-out failed.",
            command_preview=" ".join(logout_argv),
            output=output,
        )
    invalidate_runtime_snapshot_cache()
    refreshed = _runtime_target("cursor")
    if bool(dict((refreshed or {}).get("auth") or {}).get("logged_in")):
        return _action_result(
            status="error",
            message="Cursor sign-out did not clear authentication.",
            command_preview=" ".join(cursor_cli_argv(binary, "status")),
            output=output,
        )
    return _action_result(
        status="completed",
        message="Cursor CLI signed out.",
        command_preview=" ".join(cursor_cli_argv(binary, "status")),
        output=output,
    )


def logout_codex_runtime() -> StatusRecord:
    binary = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())
    target = _runtime_target("codex", force_refresh=False)
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
            env={**codex_profile_env(), "NO_COLOR": "1"},
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
    # Prefer cached status for the already-signed-in short-circuit; a forced
    # probe here can take >15s and starve the login response.
    target = _runtime_target("cursor", force_refresh=False)
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Install Cursor CLI before signing in.",
            force_refresh=False,
        )
    if auth.get("logged_in") and auth.get("auth_method") == "oauth":
        account = str(auth.get("account_label") or "").strip()
        notice = _host_cli_oauth_notice("Cursor CLI")
        return _action_result(
            status="completed",
            message=(
                f"Cursor CLI is already signed in{(': ' + account) if account else ''}. "
                f"{notice}"
            ),
            command_preview=" ".join(cursor_cli_argv(binary, "status")),
            account_scope_notice=notice,
            force_refresh=False,
        )
    command = cursor_cli_argv(binary, "login")
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
            force_refresh=False,
        )
    return _action_result(
        status="browser_opened",
        message="Cursor login started — complete the browser flow on this host, then refresh status.",
        command_preview=" ".join(command),
        force_refresh=False,
    )


def start_codex_runtime_login() -> StatusRecord:
    binary = find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip())
    target = _runtime_target("codex", force_refresh=False)
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Install Codex CLI before signing in.",
            force_refresh=False,
        )
    if auth.get("logged_in") and auth.get("auth_method") in {"oauth", "chatgpt"}:
        account = str(auth.get("account_label") or "").strip()
        notice = _host_cli_oauth_notice("Codex CLI")
        return _action_result(
            status="completed",
            message=(
                f"Codex CLI is already signed in{(': ' + account) if account else ''}. "
                f"{notice}"
            ),
            command_preview=f"{binary} login status",
            account_scope_notice=notice,
            force_refresh=False,
        )
    command = [binary, "login"]
    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env={**codex_profile_env(), "NO_COLOR": "1"},
        )
    except OSError as exc:
        return _action_result(
            status="manual_required",
            message=f"Could not start Codex login on this host: {exc}. Run `{' '.join(command)}` in a terminal.",
            command_preview=" ".join(command),
            force_refresh=False,
        )
    return _action_result(
        status="browser_opened",
        message="Codex login started in Axon-X's isolated profile — complete the browser flow, then refresh status.",
        command_preview=" ".join(command),
        account_scope_notice="This Axon-X Codex profile is isolated from Cursor and other desktop sessions.",
        force_refresh=False,
    )


def logout_claude_runtime() -> StatusRecord:
    binary = find_claude_cli(os.environ.get("AXON_WATCH_CLAUDE_CLI_PATH", "").strip())
    target = _runtime_target("claude", force_refresh=False)
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Claude Code CLI is not installed on this host.",
        )
    if auth.get("auth_method") in {"api_key", "vault_api_key"}:
        return _action_result(
            status="manual_required",
            message="Claude is authenticated via API key. Remove ANTHROPIC_API_KEY from /vault or the shell env to sign out.",
            command_preview=f"{binary} auth status",
        )
    if auth.get("auth_method") in {"oauth", "claude.ai"}:
        notice = _host_cli_oauth_notice("Claude Code CLI")
        return _action_result(
            status="manual_required",
            message=(
                "Claude Code CLI sign-out is host-profile scoped, so Axon-X will not "
                "run `claude auth logout` from the console. Run it manually only if "
                "you intend to sign this host profile out of Claude Code."
            ),
            command_preview=f"{binary} auth logout",
            account_scope_notice=notice,
            force_refresh=False,
        )
    if not auth.get("logged_in"):
        return _action_result(
            status="completed",
            message="Claude Code CLI is already signed out.",
            command_preview=f"{binary} auth status",
        )
    try:
        proc = subprocess.run(
            [binary, "auth", "logout"],
            capture_output=True,
            text=True,
            timeout=12,
            env={**os.environ, "NO_COLOR": "1"},
        )
    except subprocess.TimeoutExpired:
        return _action_result(
            status="error",
            message="Claude sign-out timed out. Run `claude auth logout` on the host.",
            command_preview=f"{binary} auth logout",
        )
    output = (proc.stdout or proc.stderr or "").strip()
    if proc.returncode != 0:
        return _action_result(
            status="error",
            message=output or "Claude sign-out failed.",
            command_preview=f"{binary} auth logout",
            output=output,
        )
    invalidate_runtime_snapshot_cache()
    refreshed = _runtime_target("claude")
    if bool(dict((refreshed or {}).get("auth") or {}).get("logged_in")):
        return _action_result(
            status="error",
            message="Claude sign-out did not clear authentication.",
            command_preview=f"{binary} auth status",
            output=output,
        )
    return _action_result(
        status="completed",
        message="Claude Code CLI signed out.",
        command_preview=f"{binary} auth status",
        output=output,
    )


def start_claude_runtime_login() -> StatusRecord:
    binary = find_claude_cli(os.environ.get("AXON_WATCH_CLAUDE_CLI_PATH", "").strip())
    target = _runtime_target("claude", force_refresh=False)
    auth = dict((target or {}).get("auth") or {})
    if not binary:
        return _action_result(
            status="manual_required",
            message="Install Claude Code CLI before signing in.",
            force_refresh=False,
        )
    if auth.get("logged_in") and auth.get("auth_method") in {"oauth", "claude.ai"}:
        account = str(auth.get("account_label") or "").strip()
        notice = _host_cli_oauth_notice("Claude Code CLI")
        return _action_result(
            status="completed",
            message=(
                f"Claude Code CLI is already signed in{(': ' + account) if account else ''}. "
                f"{notice}"
            ),
            command_preview=f"{binary} auth status",
            account_scope_notice=notice,
            force_refresh=False,
        )
    command = [binary, "auth", "login"]
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
            message=f"Could not start Claude login on this host: {exc}. Run `{' '.join(command)}` in a terminal.",
            command_preview=" ".join(command),
            force_refresh=False,
        )
    return _action_result(
        status="browser_opened",
        message="Claude login started — complete the browser flow on this host, then refresh status.",
        command_preview=" ".join(command),
        force_refresh=False,
    )
