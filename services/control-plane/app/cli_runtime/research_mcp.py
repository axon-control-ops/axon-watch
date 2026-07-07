"""Ensure the audited Axon-X research MCP server is configured for Cursor CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from app.research.availability import research_capability_snapshot


def _control_plane_root() -> Path:
    # parents[2] -> services/control-plane (package root for `python -m app.*`)
    return Path(__file__).resolve().parents[2]


def _research_python_binary() -> str:
    override = str(os.environ.get("AXON_WATCH_PYTHON", "")).strip()
    if override:
        return override
    repo_root = _control_plane_root().parents[1]
    venv_python = repo_root / ".venv" / "bin" / "python3"
    if venv_python.is_file():
        return str(venv_python)
    return "python3"


def ensure_workspace_research_mcp(workspace_root: Path) -> bool:
    snapshot = research_capability_snapshot()
    if not snapshot.get("available"):
        return False

    cursor_dir = workspace_root / ".cursor"
    cursor_dir.mkdir(parents=True, exist_ok=True)
    config_path = cursor_dir / "mcp.json"

    server_entry = {
        "command": _research_python_binary(),
        "args": ["-m", "app.research.mcp_server"],
        "cwd": str(_control_plane_root()),
        "env": {
            "PYTHONPATH": str(_control_plane_root()),
        },
    }

    payload: dict[str, object] = {"mcpServers": {}}
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                servers = existing.get("mcpServers")
                payload = existing if isinstance(servers, dict) else {"mcpServers": {}}
        except json.JSONDecodeError:
            payload = {"mcpServers": {}}

    servers = payload.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        servers = {}
        payload["mcpServers"] = servers
    servers["axon-research"] = server_entry
    config_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return True
