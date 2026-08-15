"""Optional model-assisted Lead plan when deterministic decompose is ambiguous."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from app.workspace_agents.lead_task_plan import (
    LeadPlanRosterMember,
    LeadTaskPlan,
    LeadTaskPlanItem,
    acceptance_for,
    available_specialists,
    extract_exclusive_paths,
    fallback_single_owner_plan,
    normalize_roster,
    serialize_overlapping_paths,
    topo_order,
)
from app.workspace_agents.teammate_route import normalize_teammate_role

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)
_SPECIALIST_ROLES = frozenset({"frontend", "backend", "integrations", "watcher"})


def build_lead_plan_model_prompt(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember],
) -> str:
    specialists = available_specialists(roster)
    lines = [
        "Decompose this operator goal into specialist plan items for a company Lead.",
        "Return ONLY JSON of the form:",
        '{"items":[{"owner_role":"frontend|backend|integrations|watcher",'
        '"goal":"...","dependencies":[],"acceptance_criteria":"..."}]}',
        "Rules:",
        "- Only use roles present in the roster specialists below.",
        "- Prefer the minimal set of roles that must actually work.",
        "- Tailor each goal to that role; do not copy the same sentence to everyone.",
        "- dependencies are 0-based indexes into items (or empty).",
        "- Do not invent lead/overview roles.",
        "",
        "Roster specialists:",
    ]
    for member in specialists:
        lines.append(f"- role={member.role}; name={member.name}; owns={member.owns}")
    lines.extend(["", "Goal:", goal.strip()])
    return "\n".join(lines)


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = str(text or "").strip()
    if not cleaned:
        return None
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    match = _JSON_OBJECT_RE.search(cleaned)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def plan_from_model_payload(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    payload: dict[str, Any],
) -> LeadTaskPlan | None:
    members = normalize_roster(roster)
    specialists = available_specialists(members)
    allowed = {member.role for member in specialists}
    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        return None

    draft: list[dict[str, Any]] = []
    for row in raw_items:
        if not isinstance(row, dict):
            continue
        role = normalize_teammate_role(str(row.get("owner_role") or ""))
        if role not in allowed or role not in _SPECIALIST_ROLES:
            continue
        item_goal = " ".join(str(row.get("goal") or "").split()).strip()
        if not item_goal:
            item_goal = goal
        deps_raw = row.get("dependencies")
        deps_idx: list[int] = []
        if isinstance(deps_raw, list):
            for dep in deps_raw:
                try:
                    deps_idx.append(int(dep))
                except (TypeError, ValueError):
                    continue
        acceptance = " ".join(str(row.get("acceptance_criteria") or "").split()).strip()
        draft.append(
            {
                "owner_role": role,
                "goal": item_goal,
                "deps_idx": deps_idx,
                "acceptance": acceptance,
            }
        )
    if not draft:
        return None

    items: list[LeadTaskPlanItem] = []
    for index, row in enumerate(draft, start=1):
        role = str(row["owner_role"])
        plan_key = f"plan-{index:02d}-{role}"
        scoped = extract_exclusive_paths(str(row["goal"]))
        acceptance = str(row["acceptance"]) or acceptance_for(str(row["goal"]), role)
        items.append(
            LeadTaskPlanItem(
                plan_key=plan_key,
                goal=str(row["goal"]),
                owner_role=role,
                acceptance_criteria=acceptance,
                dependencies=[],
                exclusive_paths=scoped,
                allowed_paths=list(scoped),
            )
        )

    for index, row in enumerate(draft):
        deps: list[str] = []
        for dep_idx in row["deps_idx"]:
            if dep_idx < 0 or dep_idx >= len(items) or dep_idx == index:
                continue
            deps.append(items[dep_idx].plan_key)
        items[index].dependencies = list(dict.fromkeys(deps))

    items = serialize_overlapping_paths(items)
    ordered = topo_order(items)
    return LeadTaskPlan(
        goal=" ".join((goal or "").split()).strip(),
        mode="decompose",
        items=items,
        ordered_keys=ordered,
        ambiguous=False,
    )


def apply_model_lead_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    workspace_id: str,
    dispatch_runtime: Callable[..., dict[str, Any]] | None = None,
) -> LeadTaskPlan | None:
    """Ask the model for a JSON plan. Returns None on failure (caller fail-opens)."""
    members = normalize_roster(roster)
    if dispatch_runtime is None:
        from app.workspace_agents.teammate_route import dispatch_model_tiebreak

        dispatch_runtime = dispatch_model_tiebreak

    prompt = build_lead_plan_model_prompt(goal=goal, roster=members)
    try:
        payload = dispatch_runtime(
            workspace_id=workspace_id,
            composer_mode="ask",
            user_prompt=prompt,
            context_block=(
                "You are planning specialist assignments for a Lead. Return JSON only."
            ),
            execution_access="consultative",
        )
    except Exception:
        return None

    content = str(payload.get("content") or "")
    parsed = _extract_json_object(content)
    if not isinstance(parsed, dict):
        return None
    return plan_from_model_payload(goal=goal, roster=members, payload=parsed)


def resolve_lead_task_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    mode: str = "auto",
    workspace_id: str | None = None,
    use_model: bool = True,
    dispatch_runtime: Callable[..., dict[str, Any]] | None = None,
) -> LeadTaskPlan:
    """Deterministic plan first; model enrich when empty/ambiguous; fail-open single owner."""
    from app.workspace_agents.lead_task_plan import PlanMode, build_lead_task_plan

    typed_mode: PlanMode
    if mode in {"auto", "fan_out", "sequential", "decompose"}:
        typed_mode = mode  # type: ignore[assignment]
    else:
        typed_mode = "auto"

    plan = build_lead_task_plan(goal=goal, roster=roster, mode=typed_mode)
    needs_model = (not plan.items) or plan.ambiguous
    if needs_model and use_model and workspace_id and plan.mode == "decompose":
        modeled = apply_model_lead_plan(
            goal=goal,
            roster=roster,
            workspace_id=workspace_id,
            dispatch_runtime=dispatch_runtime,
        )
        if modeled is not None and modeled.items:
            return modeled
    if not plan.items:
        return fallback_single_owner_plan(goal=goal, roster=roster)
    if (
        plan.mode == "decompose"
        and plan.ambiguous
        and len({item.owner_role for item in plan.items}) > 1
    ):
        # The model tie-break was unavailable, unusable, or came back empty,
        # and the deterministic pass only produced an unconfident multi-role
        # fan-out (see _owners_for_clause). Fail safe to one confident owner
        # rather than dispatching mismatched specialists on a keyword tie.
        return fallback_single_owner_plan(goal=goal, roster=roster)
    return plan


__all__ = [
    "apply_model_lead_plan",
    "build_lead_plan_model_prompt",
    "plan_from_model_payload",
    "resolve_lead_task_plan",
]
