"""Lead (Dana) task planner — goal + roster → ordered plan items (Gate 5 slice 1).

Pure planning only. Persistence maps plan_key → task_id later via task_store.
Supports fan_out (broadcast), sequential (then-chains), and decompose (task-aware subset).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Literal

from app.workspace_agents.teammate_route import (
    MIN_MARGIN,
    MIN_WINNER_SCORE,
    score_teammate_role,
)
from app.workspace_agents.lead_query_intent import detect_specialist_query_intent

PlanMode = Literal["auto", "fan_out", "sequential", "decompose"]

_SPECIALIST_ROLES = frozenset({"frontend", "backend", "integrations", "watcher"})
_SKIP_PLAN_ROLES = frozenset({"lead", "overview_agent"})
_FAN_OUT_RE = re.compile(
    r"\b(?:check|ask|poll|sync|brief|consult)\b.{0,40}\b(?:all|every|each)\b.{0,40}"
    r"\b(?:sub[- ]?agents?|teammates?|specialists?|agents?|roles?)\b"
    r"|\b(?:all|every|each)\b.{0,20}\b(?:sub[- ]?agents?|teammates?|specialists?)\b"
    # Operator assign-all / get-to-work (not status-check phrasing).
    r"|\b(?:assign|dispatch|hand\s*off|kick\s*off|start)\b.{0,48}"
    r"\b(?:all|every|each|the)\b.{0,24}"
    r"\b(?:sub[- ]?agents?|teammates?|specialists?|agents?|roles?|team)\b"
    r"|\b(?:all|every|each)\b.{0,24}"
    r"\b(?:sub[- ]?agents?|teammates?|specialists?|agents?)\b.{0,40}"
    r"\b(?:start|work|working|go)\b"
    r"|\bget\b.{0,24}\b(?:all|every|the)\b.{0,16}"
    r"\b(?:agents?|teammates?|specialists?|team)\b.{0,24}\b(?:work|working|started?)\b"
    r"|\bmaterialize[_\s-]lead[_\s-]fan[_\s-]out\b|\baxon-assign\b|\bfan(?:ning|ned)?[\s-]?(?:this|it|that|them)?[\s-]?out\b"
    r"|\b(?:assign|dispatch|route|lease|queue)\b.{0,160}\b(?:two|three|\d+)\b"
    r".{0,120}\b(?:frontend|ui|backend|integrations?|watcher)\b.{0,120}"
    r"\b(?:frontend|ui|backend|integrations?|watcher|specialists?)\b",
    re.I | re.S,
)
_THEN_SPLIT_RE = re.compile(
    r"\b(?:then|after that|afterwards|next|followed by|and then)\b",
    re.I,
)
_ALSO_SPLIT_RE = re.compile(
    r"\b(?:and also|as well as|plus)\b",
    re.I,
)
_PATH_RE = re.compile(
    r"(?:^|[\s`\"'(])((?:app|apps|components|features|hooks|lib|locales|screens|services|packages|docs|tests|src)/[\w./\-]+)",
    re.I,
)

_ROLE_FOCUS: dict[str, str] = {
    "frontend": "UI/screen/component",
    "backend": "API/service/persistence",
    "integrations": "CI/connector/workflow",
    "watcher": "signals/health/alerts",
}

_IMPLEMENT_RE = re.compile(
    r"\b(?:fix(?:es|ed|ing)?|wire|implement|build|repair|ship|patch|update|add|remove|migrate|improve|polish|revise|clarify)\b"
    r"|make\s+(?:it|this|that|the\s+(?:screen|flow|page|dashboard|copy|ux|ui))\s+make\s+sense",
    re.I,
)

# Team "Try again" / shift continuation drafts — Lead must own these in Lane B,
# not auto-decompose into specialists (that left last_outcome stuck on Gate 6).
_EMPLOYEE_SHIFT_RETRY_RE = re.compile(
    r"(?:"
    r"retry that bounded shift now as me|"
    r"i will retry my bounded continuous shift|"
    r"continue my interrupted shift|"
    r"my last continuous shift on .{1,160} failed"
    r")",
    re.I | re.S,
)


def is_employee_shift_retry_request(goal: str) -> bool:
    """True when the operator (or Team Try again) asked to retry this role's last shift."""
    cleaned = " ".join(str(goal or "").split()).strip()
    if not cleaned:
        return False
    return bool(_EMPLOYEE_SHIFT_RETRY_RE.search(cleaned))


@dataclass(frozen=True)
class LeadPlanRosterMember:
    role: str
    name: str = ""
    owns: str = ""


@dataclass
class LeadTaskPlanItem:
    plan_key: str
    goal: str
    owner_role: str
    acceptance_criteria: str = ""
    dependencies: list[str] = field(default_factory=list)
    risk: str = "normal"
    exclusive_paths: list[str] = field(default_factory=list)
    allowed_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeadTaskPlan:
    goal: str
    mode: PlanMode
    items: list[LeadTaskPlanItem]
    ordered_keys: list[str]
    ambiguous: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "mode": self.mode,
            "items": [item.to_dict() for item in self.items],
            "ordered_keys": list(self.ordered_keys),
            "ambiguous": self.ambiguous,
        }


def detect_fan_out_intent(goal: str) -> bool:
    return bool(_FAN_OUT_RE.search(goal or ""))


def detect_implement_intent(goal: str) -> bool:
    return bool(_IMPLEMENT_RE.search(goal or ""))


def extract_exclusive_paths(text: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for match in _PATH_RE.finditer(text or ""):
        path = match.group(1).strip().rstrip(".,);:]")
        key = path.lower()
        if key and key not in seen:
            seen.add(key)
            found.append(path)
    return found


def normalize_roster(roster: list[LeadPlanRosterMember] | list[dict[str, Any]]) -> list[LeadPlanRosterMember]:
    members: list[LeadPlanRosterMember] = []
    for row in roster:
        if isinstance(row, LeadPlanRosterMember):
            members.append(row)
            continue
        role = str(row.get("role") or "").strip().lower()
        if not role:
            continue
        members.append(
            LeadPlanRosterMember(
                role=role,
                name=str(row.get("name") or "").strip(),
                owns=str(row.get("owns") or "").strip(),
            )
        )
    return members


def available_specialists(roster: list[LeadPlanRosterMember]) -> list[LeadPlanRosterMember]:
    out: list[LeadPlanRosterMember] = []
    seen: set[str] = set()
    for member in roster:
        role = member.role.strip().lower()
        if role in _SKIP_PLAN_ROLES or role not in _SPECIALIST_ROLES:
            continue
        if role in seen:
            continue
        seen.add(role)
        out.append(member)
    return out


def _score_specialists(
    text: str,
    specialists: list[LeadPlanRosterMember],
) -> list[tuple[LeadPlanRosterMember, int]]:
    scored = [
        (member, score_teammate_role(text, member.role, member.owns))
        for member in specialists
    ]
    scored.sort(key=lambda pair: (-pair[1], pair[0].role))
    return scored


def _best_owner_role(goal: str, specialists: list[LeadPlanRosterMember]) -> str:
    if not specialists:
        return "backend"
    scored = _score_specialists(goal, specialists)
    best_score, best_role = scored[0][1], scored[0][0].role
    if best_score > 0:
        return best_role
    # Prefer backend when bags are silent — durable work default.
    roles = {member.role for member in specialists}
    if "backend" in roles:
        return "backend"
    return specialists[0].role


def _owners_for_clause(
    clause: str,
    specialists: list[LeadPlanRosterMember],
) -> tuple[list[LeadPlanRosterMember], bool]:
    """Return clear owners for a clause and whether scoring was ambiguous."""
    if not specialists:
        return [], True
    scored = _score_specialists(clause, specialists)
    eligible = [(member, score) for member, score in scored if score >= MIN_WINNER_SCORE]
    if len(eligible) >= 2:
        # Require every winner to clear the higher bar before automatic fan-out.
        decisive = all(score >= MIN_WINNER_SCORE + MIN_MARGIN for _member, score in eligible)
        return [member for member, _score in eligible], not decisive
    if len(eligible) == 1:
        return [eligible[0][0]], False
    # Soft winner: positive score but below hard threshold — ambiguous for model.
    if scored[0][1] > 0:
        winner, winner_score = scored[0]
        second_score = scored[1][1] if len(scored) > 1 else 0
        if winner_score - second_score >= MIN_MARGIN:
            return [winner], False
        return [winner], True
    return [], True


def _tailored_goal(clause: str, role: str, owns: str, multi: bool) -> str:
    focus = _ROLE_FOCUS.get(role, role)
    owns_bit = f" ({owns})" if owns.strip() else ""
    if multi:
        return f"{role.title()}: address {focus} aspects{owns_bit} of: {clause}"
    return clause


def acceptance_for(goal: str, owner_role: str) -> str:
    trimmed = " ".join((goal or "").split()).strip()
    return (
        f"Receipts prove {owner_role} completed: {trimmed[:160]}"
        if trimmed
        else f"Receipts prove {owner_role} completed the assigned work"
    )


def serialize_overlapping_paths(items: list[LeadTaskPlanItem]) -> list[LeadTaskPlanItem]:
    """If two items share exclusive_paths, chain the later behind the earlier."""
    path_owner: dict[str, str] = {}
    for item in items:
        blockers: list[str] = []
        for path in item.exclusive_paths:
            key = path.lower()
            prior = path_owner.get(key)
            if prior and prior != item.plan_key and prior not in item.dependencies:
                blockers.append(prior)
            path_owner[key] = item.plan_key
        if blockers:
            item.dependencies = list(dict.fromkeys([*item.dependencies, *blockers]))
    return items


def topo_order(items: list[LeadTaskPlanItem]) -> list[str]:
    by_key = {item.plan_key: item for item in items}
    pending = set(by_key)
    ordered: list[str] = []
    while pending:
        ready = sorted(
            key
            for key in pending
            if all(dep not in pending for dep in by_key[key].dependencies)
        )
        if not ready:
            # Cycle fallback — keep remaining in input order.
            ordered.extend(sorted(pending))
            break
        for key in ready:
            ordered.append(key)
            pending.remove(key)
    return ordered


def _split_clauses(goal: str) -> list[str]:
    then_parts = [
        part.strip(" ,.;")
        for part in _THEN_SPLIT_RE.split(goal)
        if part and part.strip(" ,.;")
    ] or [goal]
    clauses: list[str] = []
    for part in then_parts:
        also_parts = [
            chunk.strip(" ,.;")
            for chunk in _ALSO_SPLIT_RE.split(part)
            if chunk and chunk.strip(" ,.;")
        ]
        if len(also_parts) > 1:
            clauses.extend(also_parts)
        else:
            clauses.append(part)
    return clauses or [goal]


def _build_fan_out_items(
    cleaned_goal: str,
    specialists: list[LeadPlanRosterMember],
) -> list[LeadTaskPlanItem]:
    if not specialists:
        raise ValueError("fan_out requires at least one specialist role in the roster")
    items: list[LeadTaskPlanItem] = []
    for index, member in enumerate(specialists, start=1):
        role_goal = f"[{member.role}] Review and report on: {cleaned_goal}"
        scoped = extract_exclusive_paths(cleaned_goal)
        items.append(
            LeadTaskPlanItem(
                plan_key=f"plan-{index:02d}-{member.role}",
                goal=role_goal,
                owner_role=member.role,
                acceptance_criteria=acceptance_for(cleaned_goal, member.role),
                dependencies=[],
                exclusive_paths=scoped,
                allowed_paths=list(scoped),
            )
        )
    return serialize_overlapping_paths(items)


def _build_sequential_items(
    cleaned_goal: str,
    specialists: list[LeadPlanRosterMember],
) -> list[LeadTaskPlanItem]:
    clauses = _split_clauses(cleaned_goal)
    items: list[LeadTaskPlanItem] = []
    previous_key: str | None = None
    for index, clause in enumerate(clauses, start=1):
        owner = _best_owner_role(clause, specialists)
        plan_key = f"plan-{index:02d}-{owner}"
        deps = [previous_key] if previous_key else []
        scoped = extract_exclusive_paths(clause)
        items.append(
            LeadTaskPlanItem(
                plan_key=plan_key,
                goal=clause,
                owner_role=owner,
                acceptance_criteria=acceptance_for(clause, owner),
                dependencies=deps,
                exclusive_paths=scoped,
                allowed_paths=list(scoped),
            )
        )
        previous_key = plan_key
    return serialize_overlapping_paths(items)


def _build_decompose_items(
    cleaned_goal: str,
    specialists: list[LeadPlanRosterMember],
) -> tuple[list[LeadTaskPlanItem], bool]:
    clauses = _split_clauses(cleaned_goal)
    items: list[LeadTaskPlanItem] = []
    ambiguous = False
    previous_keys: list[str] = []
    counter = 0
    for clause in clauses:
        owners, clause_ambiguous = _owners_for_clause(clause, specialists)
        ambiguous = ambiguous or clause_ambiguous
        if not owners:
            ambiguous = True
            continue
        multi = len(owners) > 1
        clause_keys: list[str] = []
        scoped = extract_exclusive_paths(clause)
        for member in owners:
            counter += 1
            plan_key = f"plan-{counter:02d}-{member.role}"
            # Parallel within a clause; chain onto prior clause keys when then-split.
            deps = list(previous_keys) if previous_keys else []
            items.append(
                LeadTaskPlanItem(
                    plan_key=plan_key,
                    goal=_tailored_goal(
                        clause,
                        member.role,
                        member.owns,
                        multi=multi or len(clauses) > 1,
                    ),
                    owner_role=member.role,
                    acceptance_criteria=acceptance_for(clause, member.role),
                    dependencies=deps,
                    exclusive_paths=list(scoped),
                    allowed_paths=list(scoped),
                )
            )
            clause_keys.append(plan_key)
        previous_keys = clause_keys
    if not items:
        ambiguous = True
    return serialize_overlapping_paths(items), ambiguous


def build_lead_task_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    mode: PlanMode = "auto",
) -> LeadTaskPlan:
    cleaned_goal = " ".join((goal or "").split()).strip()
    if not cleaned_goal:
        raise ValueError("goal is required")

    members = normalize_roster(roster)
    specialists = available_specialists(members)
    resolved_mode: PlanMode = mode
    if mode == "auto":
        resolved_mode = "fan_out" if detect_fan_out_intent(cleaned_goal) else "decompose"

    ambiguous = False
    if resolved_mode == "fan_out":
        items = _build_fan_out_items(cleaned_goal, specialists)
    elif resolved_mode == "sequential":
        items = _build_sequential_items(cleaned_goal, specialists)
    else:
        # decompose (and any unknown treated as decompose)
        resolved_mode = "decompose"
        items, ambiguous = _build_decompose_items(cleaned_goal, specialists)

    ordered = topo_order(items)
    return LeadTaskPlan(
        goal=cleaned_goal,
        mode=resolved_mode,
        items=items,
        ordered_keys=ordered,
        ambiguous=ambiguous,
    )


def fallback_single_owner_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
) -> LeadTaskPlan:
    """Fail-open single specialist when decompose/model yields nothing usable."""
    cleaned_goal = " ".join((goal or "").split()).strip()
    members = normalize_roster(roster)
    specialists = available_specialists(members)
    owner = _best_owner_role(cleaned_goal, specialists)
    scoped = extract_exclusive_paths(cleaned_goal)
    item = LeadTaskPlanItem(
        plan_key=f"plan-01-{owner}",
        goal=cleaned_goal,
        owner_role=owner,
        acceptance_criteria=acceptance_for(cleaned_goal, owner),
        exclusive_paths=scoped,
        allowed_paths=list(scoped),
    )
    return LeadTaskPlan(
        goal=cleaned_goal,
        mode="decompose",
        items=[item],
        ordered_keys=[item.plan_key],
        ambiguous=False,
    )


def should_lead_decompose_dispatch(plan: LeadTaskPlan) -> bool:
    """Whether Lead IDE should materialize this plan instead of a Lane B essay."""
    if plan.mode == "fan_out":
        return False
    if is_employee_shift_retry_request(plan.goal):
        return False
    if not plan.items:
        return False
    if any(item.owner_role == "lead" for item in plan.items):
        return False
    if len(plan.items) >= 2:
        return True
    return detect_implement_intent(plan.goal) or detect_specialist_query_intent(plan.goal)


__all__ = [
    "LeadPlanRosterMember",
    "LeadTaskPlan",
    "LeadTaskPlanItem",
    "PlanMode",
    "build_lead_task_plan",
    "detect_fan_out_intent",
    "detect_implement_intent",
    "extract_exclusive_paths",
    "fallback_single_owner_plan",
    "is_employee_shift_retry_request",
    "should_lead_decompose_dispatch",
    # Shared with lead_plan_model (stable helpers).
    "acceptance_for",
    "available_specialists",
    "normalize_roster",
    "serialize_overlapping_paths",
    "topo_order",
]
