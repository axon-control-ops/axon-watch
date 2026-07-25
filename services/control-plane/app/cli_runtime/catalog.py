"""Discover local CLI runtimes and expose a boot-safe status snapshot."""

from __future__ import annotations

import os
import shutil
from typing import Any

from app.cli_runtime.auth_probes import (
    _AUTH_PROBE_TIMEOUT_SECONDS,
    _run_command,
    codex_auth_status as _codex_auth_status,
    cursor_auth_status as _cursor_auth_status,
    vault_auth_overlay as _vault_auth_overlay,
)
from app.cli_runtime.catalog_identity import runtime_identity_snapshot
from app.cli_runtime.catalog_snapshot import (
    _SNAPSHOT_CACHE,
    _SNAPSHOT_REFRESH_THREAD,
    invalidate_runtime_snapshot_cache,
    runtime_status_snapshot,
    schedule_runtime_status_refresh,
)

StatusRecord = dict[str, Any]

__all__ = [
    "StatusRecord",
    "cli_runtime_family",
    "find_codex_cli",
    "find_cursor_cli",
    "invalidate_runtime_snapshot_cache",
    "runtime_identity_snapshot",
    "runtime_status_snapshot",
    "schedule_runtime_status_refresh",
    "_AUTH_PROBE_TIMEOUT_SECONDS",
    "_codex_auth_status",
    "_cursor_auth_status",
    "_run_command",
    "_vault_auth_overlay",
]


def cli_runtime_family(path: str = "") -> str:
    candidate = os.path.basename(str(path or "")).strip().lower()
    if candidate == "cursor":
        return "cursor"
    if "codex" in candidate:
        return "codex"
    return ""


def _is_executable(path: str) -> bool:
    return bool(path) and os.path.isfile(path) and os.access(path, os.X_OK)


def find_cursor_cli(override_path: str = "") -> str:
    if _is_executable(override_path) and cli_runtime_family(override_path) == "cursor":
        return override_path
    for candidate in (
        shutil.which("cursor") or "",
        os.path.expanduser("~/.local/bin/cursor"),
        os.path.expanduser("~/bin/cursor"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""


def find_codex_cli(override_path: str = "") -> str:
    if _is_executable(override_path) and cli_runtime_family(override_path) == "codex":
        return override_path
    for candidate in (
        shutil.which("codex") or "",
        os.path.expanduser("~/.local/bin/codex"),
        os.path.expanduser("~/bin/codex"),
        os.path.expanduser("~/.npm-global/bin/codex"),
        os.path.expanduser("~/.volta/bin/codex"),
    ):
        if _is_executable(candidate):
            return candidate
    return ""
