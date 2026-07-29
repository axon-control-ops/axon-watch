"""Assemble local and cloud records for the CLI runtime catalog."""

from __future__ import annotations

import os
from typing import Any

from app.cli_runtime.auth_probes import (
    claude_auth_status,
    codex_auth_status,
    cursor_auth_status,
)
from app.cli_runtime.catalog_records import cloud_runtime_record, local_runtime_record


def build_runtime_inventory(
    *,
    vault_posture: dict[str, Any],
    merged_env: dict[str, str],
    vault_env_only: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    # Import through the public catalog facade so existing test/operator patch points
    # remain stable after binary discovery was extracted.
    from app.cli_runtime.catalog import find_claude_cli, find_codex_cli, find_cursor_cli

    paths = {
        "cursor": find_cursor_cli(os.environ.get("AXON_WATCH_CURSOR_CLI_PATH", "").strip()),
        "claude": find_claude_cli(os.environ.get("AXON_WATCH_CLAUDE_CLI_PATH", "").strip()),
        "codex": find_codex_cli(os.environ.get("AXON_WATCH_CODEX_CLI_PATH", "").strip()),
    }
    auth_probes = {
        "cursor": cursor_auth_status,
        "claude": claude_auth_status,
        "codex": codex_auth_status,
    }
    local_labels = {
        "cursor": "Cursor CLI (local)",
        "claude": "Claude Code CLI (local)",
        "codex": "Codex CLI (local)",
    }
    local = [
        local_runtime_record(
            f"{family}_local",
            family=family,
            binary=paths[family],
            auth=auth_probes[family](
                paths[family],
                vault_posture=vault_posture,
                env_keys=vault_env_only,
                probe_env=merged_env,
            ),
            label=local_labels[family],
        )
        for family in ("cursor", "claude", "codex")
    ]
    cloud_labels = {
        "cursor": "Cursor Cloud Agent",
        "claude": "Claude Cloud Agent",
        "codex": "Codex Cloud Task",
    }
    cloud = [
        cloud_runtime_record(
            f"{family}_cloud",
            family=family,
            label=cloud_labels[family],
            vault_posture=vault_posture,
            env_keys=vault_env_only,
        )
        for family in ("cursor", "claude", "codex")
    ]
    return local, cloud
