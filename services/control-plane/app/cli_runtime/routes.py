"""Thin route helpers for runtime status surfaces."""

from __future__ import annotations

from app.cli_runtime.catalog import runtime_status_snapshot
from app.cli_runtime.cursor_models import cursor_runtime_snapshot
from app.cli_runtime.mcp_registry import runtime_mcp_tools_registry


def get_runtime_status() -> dict[str, object]:
    return runtime_status_snapshot()


def get_cursor_runtime_status(*, force_refresh: bool = False) -> dict[str, object]:
    return cursor_runtime_snapshot(force_refresh=force_refresh)


def get_runtime_mcp_tools() -> dict[str, object]:
    return runtime_mcp_tools_registry()
