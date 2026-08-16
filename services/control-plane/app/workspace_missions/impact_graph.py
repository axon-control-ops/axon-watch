"""Explicit plus evidence-backed workspace impact graph."""

from __future__ import annotations

import json
import os
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from app.persistence import handoff_store
from app.workspace_catalog import list_workspace_records


def _config_path() -> Path:
    configured = os.environ.get("AXON_WORKSPACE_DEPENDENCIES_FILE", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).resolve().parents[4] / "config" / "workspace-dependencies.json"


def load_explicit_edges() -> list[dict[str, Any]]:
    path = _config_path()
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if int(payload.get("version") or 0) != 1:
        return []
    edges = payload.get("edges")
    return [dict(row) for row in edges if isinstance(row, dict)] if isinstance(edges, list) else []


def _package_name(root: Path) -> tuple[str, set[str]]:
    path = root / "package.json"
    if not path.is_file():
        return "", set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "", set()
    dependencies: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        values = payload.get(key)
        if isinstance(values, dict):
            dependencies.update(str(item) for item in values)
    return str(payload.get("name") or "").strip(), dependencies


def _declared_cycle(source: str, target: str, rows: list[dict[str, Any]]) -> bool:
    adjacency: dict[str, set[str]] = {}
    for row in rows:
        left = str(row.get("source_workspace_id") or "").strip()
        right = str(row.get("target_workspace_id") or "").strip()
        if left and right:
            adjacency.setdefault(left, set()).add(right)
    pending = [target]
    seen: set[str] = set()
    while pending:
        current = pending.pop()
        if current == source:
            return True
        if current in seen:
            continue
        seen.add(current)
        pending.extend(adjacency.get(current, set()))
    return False


def _matches_change(row: dict[str, Any], changed_paths: list[str]) -> bool:
    patterns = row.get("evidence_globs")
    if not changed_paths or not isinstance(patterns, list) or not patterns:
        return True
    return any(
        fnmatch(path, str(pattern))
        for path in changed_paths
        for pattern in patterns
        if str(pattern).strip()
    )


def impact_edges(
    source_workspace_id: str, *, changed_paths: list[str] | None = None
) -> list[dict[str, Any]]:
    source = str(source_workspace_id or "").strip()
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    explicit = load_explicit_edges()
    records = list_workspace_records(operator_surface=True)
    workspace_ids = {str(row.get("workspace_id") or "") for row in records}
    if source not in workspace_ids:
        raise ValueError(f"source workspace not found: {source}")
    for row in explicit:
        if str(row.get("source_workspace_id") or "").strip() != source:
            continue
        if not _matches_change(row, changed_paths or []):
            continue
        target = str(row.get("target_workspace_id") or "").strip()
        if target and target != source:
            review_reason = ""
            if target not in workspace_ids:
                review_reason = "declared target workspace is not bound"
            elif _declared_cycle(source, target, explicit):
                review_reason = "declared dependency cycle requires Lead review"
            merged[(source, target)] = {
                **row, "source_workspace_id": source, "target_workspace_id": target,
                "evidence_kind": "explicit", "actionable": not review_reason,
                "confidence": 1.0, "review_reason": review_reason,
            }
    roots = {
        str(row.get("workspace_id") or ""): Path(str(row.get("project_root") or ""))
        for row in records if str(row.get("project_root") or "").strip()
    }
    source_name, _ = _package_name(roots[source]) if source in roots else ("", set())
    if source_name:
        for target, root in roots.items():
            if target == source:
                continue
            _, dependencies = _package_name(root)
            if source_name in dependencies and (source, target) not in merged:
                merged[(source, target)] = {
                    "source_workspace_id": source, "target_workspace_id": target,
                    "evidence_kind": "package_dependency", "evidence": source_name,
                    "actionable": True, "confidence": 0.95,
                    "verification_commands": [], "promotion_order": 100,
                }
    for handoff in handoff_store.list_recent_handoffs(limit=100):
        if str(handoff.get("source_workspace_id") or "") != source:
            continue
        target = str(handoff.get("target_workspace_id") or "").strip()
        key = (source, target)
        if target and key not in merged:
            merged[key] = {
                "source_workspace_id": source, "target_workspace_id": target,
                "evidence_kind": "prior_handoff", "evidence": handoff.get("handoff_id"),
                "actionable": False, "confidence": 0.6,
                "review_reason": "prior handoff alone is not enough for autonomous fan-out",
            }
    return sorted(merged.values(), key=lambda row: str(row.get("target_workspace_id") or ""))


__all__ = ["impact_edges", "load_explicit_edges"]
