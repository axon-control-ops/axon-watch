"""Static MCP tool registry exposed by the control-plane runtime surface."""

from __future__ import annotations

from app.research.availability import research_capability_snapshot


def runtime_mcp_tools_registry() -> dict[str, object]:
    items = [
        {
            "id": "workspace_files.list",
            "label": "List workspace files",
            "bounded_context": "workspace_files",
            "mode_support": ["ask", "plan", "agent", "debug"],
        },
        {
            "id": "workspace_files.read",
            "label": "Read workspace file",
            "bounded_context": "workspace_files",
            "mode_support": ["ask", "plan", "agent", "debug"],
        },
        {
            "id": "runs.history",
            "label": "Read persisted run history",
            "bounded_context": "runs",
            "mode_support": ["plan", "agent", "debug"],
        },
        {
            "id": "runtime.status",
            "label": "Inspect runtime status",
            "bounded_context": "cli_runtime",
            "mode_support": ["ask", "plan", "agent", "debug"],
        },
        {
            "id": "vault.status",
            "label": "Inspect vault posture",
            "bounded_context": "vault",
            "mode_support": ["ask", "plan", "agent", "debug"],
        },
    ]
    if research_capability_snapshot().get("available"):
        items.extend(
            [
                {
                    "id": "axon_research.search",
                    "label": "Search the public web (audited)",
                    "bounded_context": "research",
                    "mode_support": ["ask", "plan", "agent", "debug"],
                },
                {
                    "id": "axon_research.fetch",
                    "label": "Fetch readable page text (audited)",
                    "bounded_context": "research",
                    "mode_support": ["ask", "plan", "agent", "debug"],
                },
            ]
        )
    return {"count": len(items), "items": items}


def mcp_tools_for_composer_mode(composer_mode: str) -> dict[str, object]:
    """Return registry entries available for the active IDE composer mode."""
    normalized = str(composer_mode or "agent").strip().lower()
    registry = runtime_mcp_tools_registry()
    items = registry.get("items")
    if not isinstance(items, list):
        return {"count": 0, "items": []}
    filtered = [
        item
        for item in items
        if isinstance(item, dict)
        and normalized in [str(mode).lower() for mode in (item.get("mode_support") or [])]
    ]
    return {"count": len(filtered), "items": filtered}
