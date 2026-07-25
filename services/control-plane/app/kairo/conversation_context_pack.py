"""Build grounded conversation context packs for KAIRO turns."""

from __future__ import annotations

from typing import Any

from app.kairo.context_pack_cache import get_cached_context_pack
from app.operator_briefing import build_operator_briefing
from app.operator_brain_graph import build_operator_brain_graph
from app.operator_fleet_health import build_operator_fleet_health
from app.persistence import chat_store
from app.workspace_project_bindings import get_workspace_project_binding


def recent_workspace_dialogue(*, workspace_id: str | None, limit: int = 3) -> list[dict[str, str]]:
    scoped = str(workspace_id or "").strip()
    if not scoped:
        return []
    thread = chat_store.get_latest_thread_for_workspace(scoped, thread_kind="operator")
    if thread is None:
        return []
    items = chat_store.list_thread_messages(str(thread["thread_id"]))
    dialogue: list[dict[str, str]] = []
    for item in items:
        role = str(item.get("role") or "").strip()
        mapped_role = "operator" if role == "operator" else "assistant" if role == "agent" else ""
        content = str(item.get("content") or "").strip()
        if mapped_role and content:
            dialogue.append({"role": mapped_role, "content": content})
    return dialogue[-max(1, limit) :]


def build_conversation_context_pack_uncached(*, workspace_id: str | None = None) -> dict[str, Any]:
    scoped = workspace_id.strip() if workspace_id else None
    briefing = build_operator_briefing(workspace_id=scoped)
    fleet = build_operator_fleet_health()
    graph = build_operator_brain_graph()
    binding = get_workspace_project_binding(scoped) if scoped else None
    recent_dialogue = recent_workspace_dialogue(workspace_id=scoped)
    nodes = [node for node in graph.get("nodes", []) if isinstance(node, dict)]
    edges = [edge for edge in graph.get("edges", []) if isinstance(edge, dict)]
    critical_workspaces = sum(
        1
        for item in fleet.get("items", [])
        if isinstance(item, dict) and item.get("tone") == "critical"
    )
    attention_workspaces = sum(
        1
        for item in fleet.get("items", [])
        if isinstance(item, dict) and item.get("tone") == "attention"
    )
    return {
        "briefing": briefing,
        "workspace": {
            "workspace_id": scoped or str(briefing.get("scope", {}).get("workspace_id") or "").strip(),
            "display_name": (
                str(briefing.get("scope", {}).get("display_name") or "").strip()
                or str(binding.display_name if binding else "").strip()
            ),
        },
        "fleet": {
            "workspace_count": len(fleet.get("items", [])),
            "critical_count": critical_workspaces,
            "attention_count": attention_workspaces,
        },
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "recent_dialogue": recent_dialogue,
    }


def build_conversation_context_pack(
    *,
    workspace_id: str | None = None,
    force_refresh: bool = False,
) -> dict[str, Any]:
    scoped = workspace_id.strip() if workspace_id else None
    return get_cached_context_pack(
        scoped,
        lambda: build_conversation_context_pack_uncached(workspace_id=scoped),
        force_refresh=force_refresh,
    )
