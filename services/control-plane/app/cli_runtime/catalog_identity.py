"""Runtime identity projection from the CLI status snapshot."""

from __future__ import annotations

import os
from typing import Any

StatusRecord = dict[str, Any]


def runtime_identity_snapshot(*, allow_stale: bool = False) -> StatusRecord:
    from app.cli_runtime.catalog import runtime_status_snapshot

    snapshot = runtime_status_snapshot(allow_stale=allow_stale)
    default_runtime = str(snapshot.get("default_runtime") or "")
    records = [*list(snapshot.get("local") or []), *list(snapshot.get("cloud") or [])]
    selected = next((record for record in records if record.get("id") == default_runtime), None)

    if not selected:
        return {
            "provider_family": "bootstrap",
            "provider_name": "Axon-X Bootstrap",
            "model_name": "bootstrap-model",
            "mode_default": os.environ.get("AXON_WATCH_MODE_DEFAULT", "agent"),
            "tool_calling_supported": False,
            "reasoning_supported": False,
        }

    family = str(selected.get("family") or "cursor")
    if family == "cursor":
        provider_name = "Cursor CLI"
        model_name = os.environ.get("AXON_WATCH_CURSOR_MODEL", "cursor-default")
    elif family == "claude":
        provider_name = "Claude Code CLI"
        model_name = os.environ.get("AXON_WATCH_CLAUDE_MODEL", "sonnet")
    else:
        provider_name = "Codex CLI"
        model_name = os.environ.get("AXON_WATCH_CODEX_MODEL", "gpt-5.5")
    if str(selected.get("target_type") or "") == "cloud":
        if family == "cursor":
            provider_name = "Cursor Cloud Agent"
        elif family == "claude":
            provider_name = "Claude Cloud Agent"
        else:
            provider_name = "Codex Cloud Task"

    return {
        "provider_family": f"{family}_{selected.get('target_type')}",
        "provider_name": provider_name,
        "model_name": model_name,
        "mode_default": os.environ.get("AXON_WATCH_MODE_DEFAULT", "agent"),
        "tool_calling_supported": bool(selected.get("ready")),
        "reasoning_supported": bool(selected.get("available")),
    }
