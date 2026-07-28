"""Lead (Dana) task planner — goal + roster → ordered plan items (Gate 5 slice 1).

Pure planning only. Persistence maps plan_key → task_id later via task_store.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any, Literal

from app.workspace_agents.teammate_route import score_teammate_role

PlanMode = Literal["auto", "fan_out", "sequential"]

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
    r"\b(?:agents?|teammates?|specialists?|team)\b.{0,24}\b(?:work|working|started?)\b",
    re.I | re.S,
)
_THEN_SPLIT_RE = re.compile(
    r"\b(?:then|after that|afterwards|next|followed by)\b",
    re.I,
)
_PATH_RE = re.compile(
    r"(?:^|[\s`\"'(])((?:apps|services|packages|docs|tests|src)/[\w./\-]+)",
    re.I,
)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "mode": self.mode,
            "items": [item.to_dict() for item in self.items],
            "ordered_keys": list(self.ordered_keys),
        }


def detect_fan_out_intent(goal: str) -> bool:
    return bool(_FAN_OUT_RE.search(goal or ""))


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


def _normalize_roster(roster: list[LeadPlanRosterMember] | list[dict[str, Any]]) -> list[LeadPlanRosterMember]:
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


def _available_specialists(roster: list[LeadPlanRosterMember]) -> list[LeadPlanRosterMember]:
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


def _best_owner_role(goal: str, specialists: list[LeadPlanRosterMember]) -> str:
    if not specialists:
        return "backend"
    scored = sorted(
        (
            (score_teammate_role(goal, member.role, member.owns), member.role)
            for member in specialists
        ),
        key=lambda pair: (-pair[0], pair[1]),
    )
    best_score, best_role = scored[0]
    if best_score > 0:
        return best_role
    # Prefer backend when bags are silent — durable work default.
    roles = {member.role for member in specialists}
    if "backend" in roles:
        return "backend"
    return specialists[0].role


def _acceptance_for(goal: str, owner_role: str) -> str:
    trimmed = " ".join((goal or "").split()).strip()
    return (
        f"Receipts prove {owner_role} completed: {trimmed[:160]}"
        if trimmed
        else f"Receipts prove {owner_role} completed the assigned work"
    )


def _serialize_overlapping_paths(items: list[LeadTaskPlanItem]) -> list[LeadTaskPlanItem]:
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


def _topo_order(items: list[LeadTaskPlanItem]) -> list[str]:
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


def build_lead_task_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    mode: PlanMode = "auto",
) -> LeadTaskPlan:
    cleaned_goal = " ".join((goal or "").split()).strip()
    if not cleaned_goal:
        raise ValueError("goal is required")

    members = _normalize_roster(roster)
    specialists = _available_specialists(members)
    resolved_mode: PlanMode = mode
    if mode == "auto":
        resolved_mode = "fan_out" if detect_fan_out_intent(cleaned_goal) else "sequential"

    items: list[LeadTaskPlanItem] = []
    if resolved_mode == "fan_out":
        if not specialists:
            raise ValueError("fan_out requires at least one specialist role in the roster")
        for index, member in enumerate(specialists, start=1):
            role_goal = (
                f"[{member.role}] Review and report on: {cleaned_goal}"
            )
            scoped = extract_exclusive_paths(cleaned_goal)
            items.append(
                LeadTaskPlanItem(
                    plan_key=f"plan-{index:02d}-{member.role}",
                    goal=role_goal,
                    owner_role=member.role,
                    acceptance_criteria=_acceptance_for(cleaned_goal, member.role),
                    dependencies=[],
                    exclusive_paths=scoped,
                    allowed_paths=list(scoped),
                )
            )
        # Fan-out: overlapping paths serialize so specialists don't race edits.
        items = _serialize_overlapping_paths(items)
    else:
        clauses = [
            part.strip(" ,.;")
            for part in _THEN_SPLIT_RE.split(cleaned_goal)
            if part and part.strip(" ,.;")
        ] or [cleaned_goal]
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
                    acceptance_criteria=_acceptance_for(clause, owner),
                    dependencies=deps,
                    exclusive_paths=scoped,
                    allowed_paths=list(scoped),
                )
            )
            previous_key = plan_key
        items = _serialize_overlapping_paths(items)

    ordered = _topo_order(items)
    return LeadTaskPlan(
        goal=cleaned_goal,
        mode=resolved_mode,
        items=items,
        ordered_keys=ordered,
    )
