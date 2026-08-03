"""Thin route helpers for runtime status surfaces."""

from __future__ import annotations

from app.cli_runtime.catalog import (
    runtime_status_snapshot,
)
from app.cli_runtime.cursor_models import cursor_runtime_snapshot
from app.cli_runtime.mcp_registry import runtime_mcp_tools_registry
from app.cli_runtime.runtime_auth_actions import (
    logout_claude_runtime,
    logout_codex_runtime,
    logout_cursor_runtime,
    start_claude_runtime_login,
    start_codex_runtime_login,
    start_cursor_runtime_login,
)


def get_runtime_status(*, force_refresh: bool = False) -> dict[str, object]:
    if force_refresh:
        return runtime_status_snapshot(force_refresh=True)
    # Default path must stay non-blocking and must not launch a Cursor CLI
    # subprocess merely because the console mounted.  An explicit refresh or
    # an actual dispatch performs the live probe.
    return runtime_status_snapshot(allow_stale=True)


def get_cursor_runtime_status(*, force_refresh: bool = False) -> dict[str, object]:
    return cursor_runtime_snapshot(force_refresh=force_refresh)


def get_runtime_mcp_tools() -> dict[str, object]:
    return runtime_mcp_tools_registry()


def post_cursor_runtime_logout() -> dict[str, object]:
    return logout_cursor_runtime()


def post_codex_runtime_logout() -> dict[str, object]:
    return logout_codex_runtime()


def post_cursor_runtime_login_start() -> dict[str, object]:
    return start_cursor_runtime_login()


def post_codex_runtime_login_start() -> dict[str, object]:
    return start_codex_runtime_login()


def post_claude_runtime_logout() -> dict[str, object]:
    return logout_claude_runtime()


def post_claude_runtime_login_start() -> dict[str, object]:
    return start_claude_runtime_login()
