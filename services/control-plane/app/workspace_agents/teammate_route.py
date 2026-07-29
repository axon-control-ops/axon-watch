"""Deterministic + optional model tie-break teammate specialty routing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable

from app.workspace_agents import WorkspaceAgentError, build_company_roster

MIN_WINNER_SCORE = 2
MIN_MARGIN = 2

_BUILD_PLAN_PROMPT_RE = re.compile(r"^Build this plan \([^)]+\):", re.IGNORECASE)

_AMBIGUOUS_REASONS = frozenset(
    {
        "margin_too_low",
        "current_still_competitive",
        "score_too_low",
    }
)

from app.workspace_agents.teammate_route_bags import (
    _PATH_ROLE_HINTS,
    _ROLE_BAGS,
)

_JSON_OBJECT_RE = re.compile(r"\{[^{}]*\}", re.DOTALL)


@dataclass
class TeammateRouteEmployee:
    employee_id: str
    name: str
    role: str
    role_label: str
    owns: str


@dataclass
class TeammateRouteDecision:
    should_route: bool
    reason: str
    employee: TeammateRouteEmployee | None = None
    from_employee_id: str | None = None
    from_name: str | None = None
    winner_score: int | None = None
    second_score: int | None = None
    source: str = "deterministic"
    ambiguous: bool = False
    routing_receipt: str | None = None
    model_receipt: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        employee = self.employee
        return {
            "should_route": self.should_route,
            "reason": self.reason,
            "employee_id": employee.employee_id if employee else None,
            "employee_role": employee.role if employee else None,
            "employee_name": employee.name if employee else None,
            "employee_role_label": employee.role_label if employee else None,
            "employee_owns": employee.owns if employee else None,
            "from_employee_id": self.from_employee_id,
            "from_name": self.from_name,
            "winner_score": self.winner_score,
            "second_score": self.second_score,
            "source": self.source,
            "ambiguous": self.ambiguous,
            "routing_receipt": self.routing_receipt,
            "model_receipt": self.model_receipt,
        }


def normalize_teammate_role(role: str) -> str:
    cleaned = re.sub(r"[\s-]+", "_", str(role or "").strip().lower())
    if cleaned in {"ui", "ux", "front_end"}:
        return "frontend"
    if cleaned == "back_end":
        return "backend"
    return cleaned


def is_build_plan_implement_prompt(prompt_text: str) -> bool:
    return bool(_BUILD_PLAN_PROMPT_RE.match(str(prompt_text or "").strip()))


def owns_overlap_score(text: str, owns: str) -> int:
    tokens = [
        token
        for token in re.split(r"[^a-z0-9+]+", str(owns or "").lower())
        if len(token) >= 4
    ]
    if not tokens:
        return 0
    lower = text.lower()
    hits = sum(1 for token in tokens if token in lower)
    return min(hits, 3)


def score_teammate_role(text: str, role: str, owns: str) -> int:
    normalized = normalize_teammate_role(role)
    score = 0
    for bag_role, weight, patterns in _ROLE_BAGS:
        if bag_role != normalized:
            continue
        for pattern in patterns:
            if pattern.search(text):
                score += weight
    for hint_role, pattern, weight in _PATH_ROLE_HINTS:
        if hint_role == normalized and pattern.search(text):
            score += weight
    score += owns_overlap_score(text, owns)
    return score


def _employee_from_row(row: dict[str, Any]) -> TeammateRouteEmployee | None:
    employee_id = str(row.get("employee_id") or "").strip()
    if not employee_id:
        return None
    return TeammateRouteEmployee(
        employee_id=employee_id,
        name=str(row.get("name") or "").strip() or "Teammate",
        role=str(row.get("role") or "").strip() or "workspace_agent",
        role_label=str(row.get("role_label") or row.get("role") or "").strip() or "role",
        owns=str(row.get("owns") or "").strip(),
    )


def roster_employees_from_company(company_payload: dict[str, Any]) -> list[TeammateRouteEmployee]:
    company = company_payload.get("company") if isinstance(company_payload.get("company"), dict) else company_payload
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return []
    employees: list[TeammateRouteEmployee] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        employee = _employee_from_row(row)
        if employee is not None:
            employees.append(employee)
    return employees


def score_roster(
    text: str,
    employees: list[TeammateRouteEmployee],
) -> list[tuple[TeammateRouteEmployee, int]]:
    scored = [(employee, score_teammate_role(text, employee.role, employee.owns)) for employee in employees]
    scored.sort(key=lambda item: (-item[1], item[0].name.lower()))
    return scored


def should_soft_route_to_teammate(
    prompt_text: str,
    current_employee: TeammateRouteEmployee | None,
    roster: list[TeammateRouteEmployee] | None,
) -> TeammateRouteDecision:
    employees = [row for row in (roster or []) if row.employee_id.strip()]
    if len(employees) < 2:
        return TeammateRouteDecision(should_route=False, reason="roster_too_small")

    text = str(prompt_text or "").strip()
    if not text:
        return TeammateRouteDecision(should_route=False, reason="empty_prompt")
    if is_build_plan_implement_prompt(text):
        return TeammateRouteDecision(should_route=False, reason="build_plan_implement")

    from app.workspace_agents.named_assign_route import match_named_assign_employee

    named = match_named_assign_employee(text, employees)
    if named is not None:
        current_id = current_employee.employee_id.strip() if current_employee else ""
        if current_id and named.employee_id.strip() == current_id:
            return TeammateRouteDecision(
                should_route=False,
                reason="already_owning",
                employee=named,
                routing_receipt="named_assign;already_owning",
            )
        from_name = (
            (current_employee.name.strip() if current_employee else "")
            or ("teammate" if current_id else "workspace")
        )
        return TeammateRouteDecision(
            should_route=True,
            reason=f"named_assign_{normalize_teammate_role(named.role)}",
            employee=named,
            from_employee_id=current_id or None,
            from_name=from_name,
            routing_receipt=(
                f"named_assign;role={normalize_teammate_role(named.role)};"
                f"to={named.employee_id}"
            ),
        )

    scored = score_roster(text, employees)
    if not scored:
        return TeammateRouteDecision(should_route=False, reason="no_match")

    winner, winner_score = scored[0]
    second_score = scored[1][1] if len(scored) > 1 else 0

    if winner_score < MIN_WINNER_SCORE:
        return TeammateRouteDecision(
            should_route=False,
            reason="score_too_low",
            employee=winner,
            winner_score=winner_score,
            second_score=second_score,
            ambiguous=winner_score > 0,
        )
    if winner_score - second_score < MIN_MARGIN:
        return TeammateRouteDecision(
            should_route=False,
            reason="margin_too_low",
            employee=winner,
            winner_score=winner_score,
            second_score=second_score,
            ambiguous=True,
        )

    current_id = (current_employee.employee_id.strip() if current_employee else "")
    if not current_id:
        return TeammateRouteDecision(
            should_route=True,
            reason=f"role_{normalize_teammate_role(winner.role)}",
            employee=winner,
            from_name="workspace",
            winner_score=winner_score,
            second_score=second_score,
            routing_receipt=f"deterministic;role={normalize_teammate_role(winner.role)};score={winner_score}",
        )

    if winner.employee_id.strip() == current_id:
        return TeammateRouteDecision(
            should_route=False,
            reason="already_owning",
            employee=winner,
            winner_score=winner_score,
            second_score=second_score,
        )

    current_score = next(
        (score for employee, score in scored if employee.employee_id.strip() == current_id),
        0,
    )
    if winner_score - current_score < MIN_MARGIN:
        return TeammateRouteDecision(
            should_route=False,
            reason="current_still_competitive",
            employee=winner,
            winner_score=winner_score,
            second_score=current_score,
            ambiguous=True,
        )

    from_name = (current_employee.name.strip() if current_employee else "") or "teammate"
    return TeammateRouteDecision(
        should_route=True,
        reason=f"role_{normalize_teammate_role(winner.role)}",
        employee=winner,
        from_employee_id=current_id,
        from_name=from_name,
        winner_score=winner_score,
        second_score=second_score,
        routing_receipt=(
            f"deterministic;role={normalize_teammate_role(winner.role)};"
            f"score={winner_score};from={current_id}"
        ),
    )


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


def build_model_tiebreak_prompt(
    *,
    prompt: str,
    roster: list[TeammateRouteEmployee],
) -> str:
    lines = [
        "Pick the single best company employee for this operator task.",
        'Return ONLY JSON: {"employee_id":"...","role":"...","reason":"..."}',
        "Do not invent employees. Choose from this roster:",
    ]
    for employee in roster:
        lines.append(
            f"- id={employee.employee_id}; name={employee.name}; "
            f"role={employee.role}; owns={employee.owns}"
        )
    lines.extend(["", "Task:", prompt.strip()])
    return "\n".join(lines)


def dispatch_model_tiebreak(**kwargs: Any) -> dict[str, Any]:
    """Use the same runtime/model pool as VAXON for ambiguous specialty routing."""

    from app.cli_runtime.router import dispatch_ide_composer
    from app.kairo.voice_dispatch import select_vaxon_runtime

    runtime_id, _runtime_label, model, _attempts = select_vaxon_runtime()
    result = dispatch_ide_composer(
        **kwargs,
        runtime_target=runtime_id,
        runtime_model=model,
    )
    return result


def apply_model_tiebreak(
    *,
    prompt: str,
    roster: list[TeammateRouteEmployee],
    current_employee: TeammateRouteEmployee | None,
    base_decision: TeammateRouteDecision,
    dispatch_runtime: Callable[..., dict[str, Any]],
    workspace_id: str,
) -> TeammateRouteDecision:
    tiebreak_prompt = build_model_tiebreak_prompt(prompt=prompt, roster=roster)
    payload = dispatch_runtime(
        workspace_id=workspace_id,
        composer_mode="ask",
        user_prompt=tiebreak_prompt,
        context_block=(
            "You are classifying which company teammate should own the task. "
            "Return JSON only."
        ),
        execution_access="consultative",
    )
    content = str(payload.get("content") or "")
    parsed = _extract_json_object(content)
    model_receipt = {
        "selected_model": payload.get("runtime_model"),
        "runtime_id": payload.get("runtime_id"),
        "runtime_label": payload.get("runtime_label"),
        "lane": "teammate_tiebreak",
        "reason": str(payload.get("reason") or "tiebreak"),
        "fallback": not bool(payload.get("dispatched")),
        "raw": content[:500],
    }
    if not isinstance(parsed, dict):
        decision = TeammateRouteDecision(
            should_route=False,
            reason=base_decision.reason or "model_tiebreak_parse_failed",
            employee=base_decision.employee,
            winner_score=base_decision.winner_score,
            second_score=base_decision.second_score,
            source="model",
            ambiguous=True,
            routing_receipt="model_tiebreak;parse_failed",
            model_receipt=model_receipt,
        )
        return decision

    employee_id = str(parsed.get("employee_id") or "").strip()
    role = normalize_teammate_role(str(parsed.get("role") or ""))
    chosen = next((row for row in roster if row.employee_id == employee_id), None)
    if chosen is None and role:
        chosen = next((row for row in roster if normalize_teammate_role(row.role) == role), None)
    if chosen is None:
        return TeammateRouteDecision(
            should_route=False,
            reason="model_tiebreak_no_match",
            employee=base_decision.employee,
            winner_score=base_decision.winner_score,
            second_score=base_decision.second_score,
            source="model",
            ambiguous=True,
            routing_receipt="model_tiebreak;no_match",
            model_receipt=model_receipt,
        )

    current_id = current_employee.employee_id.strip() if current_employee else ""
    if current_id and chosen.employee_id == current_id:
        return TeammateRouteDecision(
            should_route=False,
            reason="already_owning",
            employee=chosen,
            winner_score=base_decision.winner_score,
            second_score=base_decision.second_score,
            source="model",
            routing_receipt="model_tiebreak;already_owning",
            model_receipt=model_receipt,
        )

    from_name = (
        (current_employee.name.strip() if current_employee else "")
        or ("teammate" if current_id else "workspace")
    )
    return TeammateRouteDecision(
        should_route=True,
        reason=f"model_{normalize_teammate_role(chosen.role)}",
        employee=chosen,
        from_employee_id=current_id or None,
        from_name=from_name,
        winner_score=base_decision.winner_score,
        second_score=base_decision.second_score,
        source="model",
        routing_receipt=f"model_tiebreak;role={normalize_teammate_role(chosen.role)}",
        model_receipt=model_receipt,
    )


def route_teammate_decision(
    *,
    workspace_id: str,
    prompt: str,
    current_employee_id: str | None = None,
    use_model_tiebreak: bool = True,
    roster: list[TeammateRouteEmployee] | None = None,
    dispatch_runtime: Callable[..., dict[str, Any]] | None = None,
) -> TeammateRouteDecision:
    cleaned_workspace = str(workspace_id or "").strip()
    if not cleaned_workspace:
        raise WorkspaceAgentError("workspace_id is required")

    if roster is None:
        company = build_company_roster(cleaned_workspace)
        roster = roster_employees_from_company({"company": company})

    current: TeammateRouteEmployee | None = None
    cleaned_current = str(current_employee_id or "").strip()
    if cleaned_current:
        current = next((row for row in roster if row.employee_id == cleaned_current), None)

    from app.workspace_agents.lead_task_plan import detect_fan_out_intent
    from app.workspace_agents.named_assign_route import match_named_assign_employee

    # Explicit "assign Cole / have Priya…" wins over fan-out and soft specialty scoring.
    named = match_named_assign_employee(prompt, roster)
    if named is not None:
        cleaned_current = current.employee_id.strip() if current else ""
        if cleaned_current and named.employee_id.strip() == cleaned_current:
            return TeammateRouteDecision(
                should_route=False,
                reason="already_owning",
                employee=named,
                from_employee_id=cleaned_current,
                from_name=current.name if current else None,
                source="deterministic",
                routing_receipt="named_assign;already_owning",
            )
        return TeammateRouteDecision(
            should_route=True,
            reason=f"named_assign_{normalize_teammate_role(named.role)}",
            employee=named,
            from_employee_id=cleaned_current or None,
            from_name=(current.name if current else None) or ("teammate" if cleaned_current else "workspace"),
            source="deterministic",
            routing_receipt=(
                f"named_assign;role={normalize_teammate_role(named.role)};"
                f"to={named.employee_id}"
            ),
        )

    # Fan-out is Lead planner territory — never collapse to a single specialty winner.
    if detect_fan_out_intent(prompt):
        return TeammateRouteDecision(
            should_route=False,
            reason="lead_fan_out",
            from_employee_id=current.employee_id if current else None,
            from_name=current.name if current else None,
            source="lead_planner",
            routing_receipt=(
                "Lead fan-out intent detected — use /api/workspaces/{id}/lead/fan-out "
                "to open concurrent specialist tasks/runs"
            ),
        )

    decision = should_soft_route_to_teammate(prompt, current, roster)
    if decision.should_route or not use_model_tiebreak:
        return decision
    if not decision.ambiguous or decision.reason not in _AMBIGUOUS_REASONS:
        return decision
    if dispatch_runtime is None:
        return decision

    return apply_model_tiebreak(
        prompt=prompt,
        roster=roster,
        current_employee=current,
        base_decision=decision,
        dispatch_runtime=dispatch_runtime,
        workspace_id=cleaned_workspace,
    )


__all__ = [
    "MIN_MARGIN",
    "MIN_WINNER_SCORE",
    "TeammateRouteDecision",
    "TeammateRouteEmployee",
    "apply_model_tiebreak",
    "build_model_tiebreak_prompt",
    "dispatch_model_tiebreak",
    "is_build_plan_implement_prompt",
    "normalize_teammate_role",
    "owns_overlap_score",
    "route_teammate_decision",
    "roster_employees_from_company",
    "score_teammate_role",
    "should_soft_route_to_teammate",
]
