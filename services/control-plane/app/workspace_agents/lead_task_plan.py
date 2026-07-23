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
    r"|\b(?:all|every|each)\b.{0,20}\b(?:sub[- ]?agents?|teammates?|specialists?)\b",
    re.I | re.S,
)
_THEN_SPLIT_RE = re.compile(
    r"\b(?:then|after that|afterwards|followed by)\b",
    re.I,
)
_PATH_RE = re.compile(
    r"(?:^|[\s`\"'(])((?:apps|services|packages|docs|tests|src)/[\w./\-]+)",
    re.I,
)
_ASSIGN_RE = re.compile(
    r"\bassign(?:ed)?\s+(?:to\s+)?(?P<name>[A-Za-z][A-Za-z'-]{1,40})\b",
    re.I,
)
_ATTACHMENT_SCOPE_RE = re.compile(
    r"\b(?:csv|bank|reconcil|paid|not\s*paid|roster|fee\s*report|attachment)\b",
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
    assignee_name: str = ""
    attachment_ids: list[str] = field(default_factory=list)
    source_message_id: str = ""
    output_artifacts: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LeadTaskPlan:
    goal: str
    mode: PlanMode
    items: list[LeadTaskPlanItem]
    ordered_keys: list[str]
    source_message_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal,
            "mode": self.mode,
            "items": [item.to_dict() for item in self.items],
            "ordered_keys": list(self.ordered_keys),
            "source_message_id": self.source_message_id,
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


def resolve_named_assignee(
    text: str,
    specialists: list[LeadPlanRosterMember],
) -> LeadPlanRosterMember | None:
    """Resolve an explicit teammate name (e.g. assign PRIYA) case-insensitively."""
    if not specialists:
        return None
    by_name = {
        member.name.strip().lower(): member
        for member in specialists
        if member.name.strip()
    }
    if not by_name:
        return None

    for match in _ASSIGN_RE.finditer(text or ""):
        candidate = match.group("name").strip().lower()
        if candidate in by_name:
            return by_name[candidate]
    return None


def item_accepts_attachments(goal: str) -> bool:
    return bool(_ATTACHMENT_SCOPE_RE.search(goal or ""))


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


def _best_owner(
    goal: str,
    specialists: list[LeadPlanRosterMember],
) -> tuple[str, str]:
    """Return (owner_role, assignee_name). Explicit names beat keyword scoring."""
    named = resolve_named_assignee(goal, specialists)
    if named is not None:
        return named.role, named.name
    if not specialists:
        return "backend", ""
    scored = sorted(
        (
            (score_teammate_role(goal, member.role, member.owns), member)
            for member in specialists
        ),
        key=lambda pair: (-pair[0], pair[1].role),
    )
    best_score, best_member = scored[0]
    if best_score > 0:
        return best_member.role, best_member.name
    roles = {member.role for member in specialists}
    if "backend" in roles:
        backend = next(member for member in specialists if member.role == "backend")
        return "backend", backend.name
    return specialists[0].role, specialists[0].name


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


def _split_sequential_clauses(goal: str) -> list[str]:
    """Split sequential work on assign boundaries first, then soft 'then' joins."""
    cleaned = " ".join((goal or "").split()).strip()
    if not cleaned:
        return []

    # Hard boundary: "... then assign PRIYA ..." keeps delegation as its own clause.
    assign_parts = re.split(
        r"\b(?:then|after that|afterwards|next|followed by)\s+(?=assign(?:ed)?\b)",
        cleaned,
        flags=re.I,
    )
    clauses: list[str] = []
    for part in assign_parts:
        soft = [
            piece.strip(" ,.;")
            for piece in _THEN_SPLIT_RE.split(part)
            if piece and piece.strip(" ,.;")
        ]
        clauses.extend(soft or [part.strip(" ,.;")])
    return [clause for clause in clauses if clause]


def _merge_adjacent_same_owner(items: list[LeadTaskPlanItem]) -> list[LeadTaskPlanItem]:
    """Collapse consecutive same-role bags so noisy 'then' prose stays one task."""
    if not items:
        return items
    merged: list[LeadTaskPlanItem] = []
    for item in items:
        if (
            merged
            and merged[-1].owner_role == item.owner_role
            and merged[-1].assignee_name == item.assignee_name
        ):
            prior = merged[-1]
            prior.goal = f"{prior.goal}; {item.goal}".strip("; ")
            prior.acceptance_criteria = _acceptance_for(prior.goal, prior.owner_role)
            prior.exclusive_paths = list(
                dict.fromkeys([*prior.exclusive_paths, *item.exclusive_paths])
            )
            prior.attachment_ids = list(
                dict.fromkeys([*prior.attachment_ids, *item.attachment_ids])
            )
            prior.output_artifacts = list(
                dict.fromkeys([*prior.output_artifacts, *item.output_artifacts])
            )
            continue
        merged.append(item)

    # Re-key and re-chain sequential dependencies after merge.
    previous_key: str | None = None
    renumbered: list[LeadTaskPlanItem] = []
    for index, item in enumerate(merged, start=1):
        plan_key = f"plan-{index:02d}-{item.owner_role}"
        item.plan_key = plan_key
        item.dependencies = [previous_key] if previous_key else []
        renumbered.append(item)
        previous_key = plan_key
    return renumbered


def build_lead_task_plan(
    *,
    goal: str,
    roster: list[LeadPlanRosterMember] | list[dict[str, Any]],
    mode: PlanMode = "auto",
    attachment_ids: list[str] | None = None,
    source_message_id: str | None = None,
) -> LeadTaskPlan:
    cleaned_goal = " ".join((goal or "").split()).strip()
    if not cleaned_goal:
        raise ValueError("goal is required")

    members = _normalize_roster(roster)
    specialists = _available_specialists(members)
    resolved_mode: PlanMode = mode
    if mode == "auto":
        resolved_mode = "fan_out" if detect_fan_out_intent(cleaned_goal) else "sequential"

    cleaned_attachments = [
        str(item).strip() for item in (attachment_ids or []) if str(item).strip()
    ]
    cleaned_source = str(source_message_id or "").strip()

    items: list[LeadTaskPlanItem] = []
    if resolved_mode == "fan_out":
        if not specialists:
            raise ValueError("fan_out requires at least one specialist role in the roster")
        for index, member in enumerate(specialists, start=1):
            role_goal = (
                f"[{member.role}] Review and report on: {cleaned_goal}"
            )
            items.append(
                LeadTaskPlanItem(
                    plan_key=f"plan-{index:02d}-{member.role}",
                    goal=role_goal,
                    owner_role=member.role,
                    acceptance_criteria=_acceptance_for(cleaned_goal, member.role),
                    dependencies=[],
                    exclusive_paths=extract_exclusive_paths(cleaned_goal),
                    assignee_name=member.name,
                    attachment_ids=(
                        list(cleaned_attachments)
                        if item_accepts_attachments(role_goal)
                        else []
                    ),
                    source_message_id=cleaned_source,
                )
            )
        # Fan-out: overlapping paths serialize so specialists don't race edits.
        items = _serialize_overlapping_paths(items)
    else:
        clauses = _split_sequential_clauses(cleaned_goal) or [cleaned_goal]
        previous_key: str | None = None
        for index, clause in enumerate(clauses, start=1):
            owner_role, assignee_name = _best_owner(clause, specialists)
            plan_key = f"plan-{index:02d}-{owner_role}"
            deps = [previous_key] if previous_key else []
            scoped_attachments = (
                list(cleaned_attachments) if item_accepts_attachments(clause) else []
            )
            items.append(
                LeadTaskPlanItem(
                    plan_key=plan_key,
                    goal=clause,
                    owner_role=owner_role,
                    acceptance_criteria=_acceptance_for(clause, owner_role),
                    dependencies=deps,
                    exclusive_paths=extract_exclusive_paths(clause),
                    assignee_name=assignee_name,
                    attachment_ids=scoped_attachments,
                    source_message_id=cleaned_source,
                )
            )
            previous_key = plan_key
        items = _merge_adjacent_same_owner(items)
        items = _serialize_overlapping_paths(items)

    ordered = _topo_order(items)
    return LeadTaskPlan(
        goal=cleaned_goal,
        mode=resolved_mode,
        items=items,
        ordered_keys=ordered,
        source_message_id=cleaned_source,
    )
