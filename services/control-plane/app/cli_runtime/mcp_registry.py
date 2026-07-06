"""Static MCP tool registry exposed by the control-plane runtime surface."""

from __future__ import annotations


def runtime_mcp_tools_registry() -> dict[str, object]:
    items = [
        {
            "id": "workspace_files.list",
            "label": "List workspace files",
            "bounded_context": "workspace_files",
            "mode_support": ["ask", "plan", "agent"],
        },
        {
            "id": "workspace_files.read",
            "label": "Read workspace file",
            "bounded_context": "workspace_files",
            "mode_support": ["ask", "plan", "agent"],
        },
        {
            "id": "runs.history",
            "label": "Read persisted run history",
            "bounded_context": "runs",
            "mode_support": ["plan", "agent"],
        },
        {
            "id": "runtime.status",
            "label": "Inspect runtime status",
            "bounded_context": "cli_runtime",
            "mode_support": ["ask", "plan", "agent"],
        },
        {
            "id": "vault.status",
            "label": "Inspect vault posture",
            "bounded_context": "vault",
            "mode_support": ["ask", "plan", "agent"],
        },
    ]
    return {"count": len(items), "items": items}
