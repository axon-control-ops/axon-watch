"""Deterministic guard against assigning Axon-X mutations to product workspaces."""

from __future__ import annotations

import re


_AXON_WORKSPACES = {"workspace_axon_local", "workspace_axon_online", "workspace_axon_watch"}
_CONTROL_PLANE_TARGET = re.compile(
    r"\b(?:axon[- ]?x|control[- ]?plane|dispatcher|scoped[- ]task gate)\b", re.IGNORECASE
)
_MUTATION_INTENT = re.compile(
    r"\b(?:add|change|edit|fix|implement|patch|repair|update|upgrade|wire)\b", re.IGNORECASE
)


def cross_workspace_mutation_blocker(*, workspace_id: str, goal: str) -> str | None:
    """Explain a clear Axon-X mutation routed into a non-Axon workspace."""
    workspace = (workspace_id or "").strip().lower()
    text = " ".join((goal or "").split())
    if not workspace or workspace in _AXON_WORKSPACES:
        return None
    if not _CONTROL_PLANE_TARGET.search(text) or not _MUTATION_INTENT.search(text):
        return None
    return (
        f"This request changes Axon-X/control-plane code, but it was submitted to "
        f"{workspace}. Send it to workspace_axon_watch; do not assign it to this "
        "product company's specialists."
    )


__all__ = ["cross_workspace_mutation_blocker"]
