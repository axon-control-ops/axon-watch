"""Runtime summary, status, and CLI auth routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.cli_runtime.routes import (
    get_cursor_runtime_status,
    get_runtime_mcp_tools,
    get_runtime_status,
    post_claude_runtime_login_start,
    post_claude_runtime_logout,
    post_codex_runtime_login_start,
    post_codex_runtime_logout,
    post_cursor_runtime_login_start,
    post_cursor_runtime_logout,
)
from app.runtime_summary import build_runtime_summary

router = APIRouter()


@router.get("/api/runtime/summary")
def runtime_summary() -> dict[str, object]:
    return build_runtime_summary()


@router.get("/api/runtime/status")
def runtime_status(force_refresh: bool = False) -> dict[str, object]:
    return get_runtime_status(force_refresh=force_refresh)


@router.post("/api/runtime/cursor/logout")
def cursor_runtime_logout() -> dict[str, object]:
    return post_cursor_runtime_logout()


@router.post("/api/runtime/cursor/login/start")
def cursor_runtime_login_start() -> dict[str, object]:
    return post_cursor_runtime_login_start()


@router.post("/api/runtime/codex/logout")
def codex_runtime_logout() -> dict[str, object]:
    return post_codex_runtime_logout()


@router.post("/api/runtime/codex/login/start")
def codex_runtime_login_start() -> dict[str, object]:
    return post_codex_runtime_login_start()


@router.post("/api/runtime/claude/logout")
def claude_runtime_logout() -> dict[str, object]:
    return post_claude_runtime_logout()


@router.post("/api/runtime/claude/login/start")
def claude_runtime_login_start() -> dict[str, object]:
    return post_claude_runtime_login_start()


@router.get("/api/runtime/cursor/status")
def cursor_runtime_status(force_refresh: bool = False) -> dict[str, object]:
    return get_cursor_runtime_status(force_refresh=force_refresh)


@router.get("/api/runtime/mcp-tools")
def runtime_mcp_tools() -> dict[str, object]:
    return get_runtime_mcp_tools()
