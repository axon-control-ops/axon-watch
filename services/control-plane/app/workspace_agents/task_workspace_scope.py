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
_HOST_TREE_TARGET = re.compile(
    r"\b(?:current|existing|host|real)\b.{0,30}\b(?:working tree|uncommitted|dirty (?:files|changes))\b",
    re.IGNORECASE,
)
_DELIVERY_INTENT = re.compile(
    r"\b(?:commit|push|prepare.{0,20}(?:delivery|release)|review.{0,20}(?:diff|changes))\b",
    re.IGNORECASE,
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


def isolated_worker_task_blocker(*, goal: str) -> str | None:
    """Reject tasks that require uncommitted state absent from worker isolation."""
    text = " ".join((goal or "").split())
    if not _HOST_TREE_TARGET.search(text) or not _DELIVERY_INTENT.search(text):
        return None
    return (
        "This request requires the real workspace's existing uncommitted changes, "
        "which are intentionally absent from disposable worker checkouts. Use the "
        "audited workspace-git/operator delivery lane with explicit paths; do not "
        "delegate it as a continuous company-worker task."
    )


__all__ = ["cross_workspace_mutation_blocker", "isolated_worker_task_blocker"]
