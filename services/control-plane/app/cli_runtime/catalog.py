"""Discover local CLI runtimes and expose a boot-safe status snapshot."""

from __future__ import annotations

from typing import Any

from app.cli_runtime.auth_probes import (
    _AUTH_PROBE_TIMEOUT_SECONDS,
    _run_command,
    claude_auth_status as _claude_auth_status,
    codex_auth_status as _codex_auth_status,
    cursor_auth_status as _cursor_auth_status,
    vault_auth_overlay as _vault_auth_overlay,
)
from app.cli_runtime.catalog_discovery import (
    cli_runtime_family,
    cursor_cli_argv,
    find_claude_cli,
    find_codex_cli,
    find_cursor_cli,
)
from app.cli_runtime.catalog_identity import runtime_identity_snapshot
from app.cli_runtime.catalog_snapshot import (
    _SNAPSHOT_CACHE,
    _SNAPSHOT_REFRESH_THREAD,
    heal_cursor_auth_probe_timeout,
    invalidate_runtime_snapshot_cache,
    recover_cursor_auth_synchronously,
    runtime_status_snapshot,
    schedule_runtime_status_refresh,
    snapshot_has_auth_probe_timeout,
)

StatusRecord = dict[str, Any]

__all__ = [
    "StatusRecord", "cli_runtime_family", "cursor_cli_argv",
    "find_claude_cli", "find_codex_cli", "find_cursor_cli",
    "heal_cursor_auth_probe_timeout", "invalidate_runtime_snapshot_cache",
    "recover_cursor_auth_synchronously", "runtime_identity_snapshot",
    "runtime_status_snapshot", "schedule_runtime_status_refresh",
    "snapshot_has_auth_probe_timeout", "_AUTH_PROBE_TIMEOUT_SECONDS",
    "_claude_auth_status", "_codex_auth_status", "_cursor_auth_status",
    "_run_command", "_vault_auth_overlay",
]
