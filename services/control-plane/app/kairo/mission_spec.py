"""Standard Mission Specification conversation artifacts for VAXON."""

from __future__ import annotations

import hashlib
import re
from typing import Any

MISSION_SPEC_FIELDS = (
    ("mission_id", "Mission ID"),
    ("mission_title", "Mission Title"),
    ("objective", "Objective"),
    ("business_context", "Business Context"),
    ("success_criteria", "Success Criteria"),
    ("deliverables", "Deliverables"),
    ("constraints", "Constraints"),
    ("dependencies", "Dependencies"),
    ("recommended_specialists", "Recommended Specialists"),
    ("estimated_complexity", "Estimated Complexity"),
    ("evidence_required", "Evidence Required"),
    ("definition_of_done", "Definition of Done"),
)

_FIELD_LABELS = {
    label.lower(): key
    for key, label in MISSION_SPEC_FIELDS
    if key != "mission_id"
}


def _clean(value: object, *, limit: int = 600) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _explicit_fields(task: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for raw_line in str(task or "").splitlines():
        line = re.sub(r"^\s*(?:#{1,4}|[-*])\s*", "", raw_line).strip()
        if ":" not in line:
            continue
        label, value = line.split(":", 1)
        key = _FIELD_LABELS.get(label.strip().lower())
        cleaned = _clean(value)
        if key and cleaned:
            fields[key] = cleaned
    return fields


def _plan_items(action: dict[str, object]) -> list[dict[str, Any]]:
    plan = action.get("plan") or {}
    items = plan.get("items", []) if isinstance(plan, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _join_unique(values: list[str], *, fallback: str) -> str:
    unique = list(dict.fromkeys(value for value in values if value))
    return "; ".join(unique) or fallback


def _mission_id(task: str, workspace_id: str, action: dict[str, object]) -> str:
    explicit = _clean(action.get("plan_id"), limit=100)
    if explicit:
        return explicit
    digest = hashlib.sha256(f"{workspace_id}\n{task}".encode("utf-8")).hexdigest()[:12]
    return f"mission-{digest}"


def build_mission_spec(
    *,
    task: str,
    workspace_id: str,
    action: dict[str, object],
) -> dict[str, str]:
    """Build all required Mission Spec fields from the conversation and Lead plan."""
    explicit = _explicit_fields(task)
    items = _plan_items(action)
    goals = [_clean(item.get("goal")) for item in items]
    acceptance = [_clean(item.get("acceptance_criteria")) for item in items]
    dependencies = [
        _clean(dependency)
        for item in items
        for dependency in item.get("dependencies", [])
        if _clean(dependency)
    ]
    roles = [_clean(item.get("owner_role"), limit=60) for item in items]
    direct_role = _clean(action.get("employee_role"), limit=60)
    if direct_role:
        roles.append(direct_role)
    path_constraints = [
        _clean(path)
        for item in items
        for key in ("exclusive_paths", "allowed_paths")
        for path in item.get(key, [])
        if _clean(path)
    ]

    objective = explicit.get("objective") or _clean(task)
    title = (
        explicit.get("mission_title")
        or _clean(objective.split(".", 1)[0], limit=110)
        or "Operator-directed mission"
    )
    item_count = max(1, len(items))
    complexity = "Low" if item_count == 1 else "Medium" if item_count == 2 else "High"
    mission_id = _mission_id(task, workspace_id, action)

    return {
        "mission_id": mission_id,
        "mission_title": title,
        "objective": objective,
        "business_context": explicit.get("business_context")
        or f"Operator-directed work in {workspace_id}.",
        "success_criteria": explicit.get("success_criteria")
        or _join_unique(
            acceptance,
            fallback="All scoped deliverables satisfy their acceptance criteria with evidence.",
        ),
        "deliverables": explicit.get("deliverables")
        or _join_unique(goals, fallback=objective),
        "constraints": explicit.get("constraints")
        or _join_unique(
            path_constraints,
            fallback="Use existing AXON-X architecture and preserve irreversible-action approval gates.",
        ),
        "dependencies": explicit.get("dependencies")
        or _join_unique(
            dependencies,
            fallback="None identified in the current Lead plan.",
        ),
        "recommended_specialists": explicit.get("recommended_specialists")
        or _join_unique(
            roles,
            fallback="Lead to select from the current workspace roster.",
        ),
        "estimated_complexity": explicit.get("estimated_complexity")
        or f"{complexity} ({item_count} planned workstream{'s' if item_count != 1 else ''}).",
        "evidence_required": explicit.get("evidence_required")
        or "Specialist receipts, verification results, and GitHub/CI status where applicable.",
        "definition_of_done": explicit.get("definition_of_done")
        or (
            "All acceptance criteria are verified, evidence is attached, and any "
            "required Operator approval is recorded."
        ),
    }


def format_mission_spec(spec: dict[str, str], *, evidence_state: str) -> str:
    """Render a Mission Specification as a readable conversation artifact."""
    lines = [f"{evidence_state}: Mission Specification"]
    for key, label in MISSION_SPEC_FIELDS:
        lines.append(f"**{label}:** {spec.get(key) or 'Unknown'}")
    return "\n".join(lines)


__all__ = ["MISSION_SPEC_FIELDS", "build_mission_spec", "format_mission_spec"]
