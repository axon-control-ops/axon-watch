"""Bounded Galaxy projection for host devices, artifacts, and open loops."""

from __future__ import annotations

from typing import Any

_MAX_HOST_ARTIFACT_NODES = 4
_MAX_OPEN_LOOP_NODES = 4


def append_host_context_nodes(
    *,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    core_node_id: str,
) -> None:
    """Project device → artifact children plus open-loop nodes (LOD-safe)."""
    try:
        from app.host_context import store as host_store
        from app.host_context.reminders import list_open_loops
    except Exception:  # noqa: BLE001
        return

    try:
        devices = host_store.list_devices(limit=2)
        artifacts = host_store.list_artifacts(limit=_MAX_HOST_ARTIFACT_NODES)
        open_loops = list_open_loops(limit=_MAX_OPEN_LOOP_NODES)
    except Exception:  # noqa: BLE001
        return

    for device in devices:
        device_id = str(device.get("device_id") or "").strip()
        if not device_id:
            continue
        node_id = f"device_{device_id}"
        nodes.append(
            {
                "node_id": node_id,
                "kind": "device",
                "label": str(device.get("hostname") or device_id),
                "tone": "attention" if device.get("status") != "online" else "nominal",
                "workspace_id": None,
                "detail": f"{device.get('platform') or 'host'} · {device.get('status') or 'unknown'}",
            }
        )
        edges.append(
            {
                "edge_id": f"hosts_{device_id}",
                "source": core_node_id,
                "target": node_id,
                "kind": "hosts",
            }
        )
        _append_device_artifacts(
            nodes=nodes,
            edges=edges,
            device_id=device_id,
            device_node_id=node_id,
            artifacts=artifacts,
        )

    for item in open_loops:
        memory_id = str(item.get("memory_id") or "").strip()
        if not memory_id:
            continue
        loop_node_id = f"loop_{memory_id}"
        priority = str(item.get("priority") or "normal")
        nodes.append(
            {
                "node_id": loop_node_id,
                "kind": "open_loop",
                "label": str(item.get("title") or memory_id),
                "tone": "critical" if priority == "high" else "attention",
                "workspace_id": str(item.get("workspace_id") or "") or None,
                "detail": str(item.get("due_at") or item.get("status") or "open"),
            }
        )
        edges.append(
            {
                "edge_id": f"tracks_{memory_id}",
                "source": core_node_id,
                "target": loop_node_id,
                "kind": "tracks",
            }
        )


def _append_device_artifacts(
    *,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
    device_id: str,
    device_node_id: str,
    artifacts: list[dict[str, Any]],
) -> None:
    for artifact in artifacts:
        if str(artifact.get("device_id") or "") != device_id:
            continue
        artifact_id = str(artifact.get("artifact_id") or "").strip()
        if not artifact_id:
            continue
        art_node_id = f"artifact_{artifact_id}"
        kind = str(artifact.get("kind") or "file")
        nodes.append(
            {
                "node_id": art_node_id,
                "kind": "media" if kind in {"image", "video", "audio"} else "artifact",
                "label": str(artifact.get("title") or artifact.get("path") or artifact_id),
                "tone": "attention" if artifact.get("sensitivity") == "sensitive" else "nominal",
                "workspace_id": str(artifact.get("workspace_id") or "") or None,
                "detail": str(artifact.get("origin") or kind),
            }
        )
        edges.append(
            {
                "edge_id": f"contains_{artifact_id}",
                "source": device_node_id,
                "target": art_node_id,
                "kind": "contains",
            }
        )
