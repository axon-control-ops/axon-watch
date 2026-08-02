"""Compact Executive Intent and Mission Memory projections for VAXON."""

from __future__ import annotations

from collections import Counter
from typing import Any

_UNKNOWN = "unknown — no verified source in current context"
_MISSION_FIELDS = (
    "Mission ID; Mission Title; Objective; Business Context; Success Criteria; "
    "Deliverables; Constraints; Dependencies; Recommended Specialists; "
    "Estimated Complexity; Evidence Required; Definition of Done"
)
_EVIDENCE_STATES = (
    "Planned; Dispatched; Observed; Verified; Completed; Operator Approved"
)


def _clean(value: object, *, limit: int = 220) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        return ""
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def _safe_presence_settings() -> dict[str, object]:
    try:
        from app.persistence.operator_presence_settings_store import load_settings

        return dict(load_settings())
    except Exception:
        return {}


def _safe_recent_plans(workspace_id: str) -> list[dict[str, Any]]:
    try:
        from app.workspace_agents import lead_plan_store

        plans = lead_plan_store.list_workspace_plans(
            workspace_id,
            limit=5,
            include_task_links=False,
        )
        for plan in plans:
            plan_id = _clean(plan.get("plan_id"), limit=100)
            plan["receipts"] = (
                lead_plan_store.list_receipts(plan_id) if plan_id else []
            )
        return plans
    except Exception:
        return []


def _first_text(*values: object) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return _UNKNOWN


def _risk_line(briefing: dict[str, Any]) -> str:
    risks = [
        _clean(item.get("title"))
        for item in briefing.get("top_signals", [])
        if isinstance(item, dict) and _clean(item.get("title"))
    ]
    degraded = briefing.get("degraded") or {}
    if isinstance(degraded, dict):
        risks.extend(
            _clean(item)
            for item in degraded.get("reasons", [])
            if _clean(item)
        )
    return "; ".join(risks[:3]) or "none evidenced in current briefing"


def _constraint_line(briefing: dict[str, Any]) -> str:
    constraints: list[str] = []
    cli_runtime = briefing.get("cli_runtime") or {}
    if isinstance(cli_runtime, dict):
        constraints.extend(
            _clean(item)
            for item in cli_runtime.get("blockers", [])
            if _clean(item)
        )
    pending = briefing.get("pending_approvals") or {}
    pending_count = int(pending.get("count", 0)) if isinstance(pending, dict) else 0
    if pending_count:
        constraints.append(f"{pending_count} operator approval(s) pending")
    return "; ".join(constraints[:3]) or "none evidenced in current briefing"


def _plan_items(plan: dict[str, Any]) -> list[dict[str, Any]]:
    payload = plan.get("plan") or {}
    items = payload.get("items", []) if isinstance(payload, dict) else []
    return [item for item in items if isinstance(item, dict)]


def _mission_memory_lines(plans: list[dict[str, Any]]) -> list[str]:
    if not plans:
        return [
            f"- Recent Missions: {_UNKNOWN}",
            f"- Mission Outcomes: {_UNKNOWN}",
            f"- Lessons Learned: {_UNKNOWN}",
            f"- Reusable Patterns: {_UNKNOWN}",
            "- Repeated Failures: none evidenced in current mission history",
        ]

    recent = [
        f"{_clean(plan.get('plan_id'), limit=70)} "
        f"[{_clean(plan.get('status'), limit=30) or 'unknown'}] "
        f"{_clean(plan.get('goal'))}"
        for plan in plans[:3]
    ]
    outcomes: list[str] = []
    lessons: list[str] = []
    patterns: list[str] = []
    failure_kinds: Counter[str] = Counter()

    for plan in plans:
        plan_id = _clean(plan.get("plan_id"), limit=70) or "unknown plan"
        status = _clean(plan.get("status"), limit=30) or "unknown"
        outcomes.append(f"{plan_id}: {status}")

        if status in {"completed", "awaiting_engagement"}:
            roles = sorted(
                {
                    _clean(item.get("owner_role"), limit=40)
                    for item in _plan_items(plan)
                    if _clean(item.get("owner_role"), limit=40)
                }
            )
            mode = _clean(plan.get("mode"), limit=40)
            pattern = " + ".join(roles)
            if mode or pattern:
                patterns.append(
                    f"{mode or 'planned'} via {pattern or 'assigned specialists'}"
                )

        for receipt in plan.get("receipts", []):
            if not isinstance(receipt, dict):
                continue
            kind = _clean(receipt.get("kind"), limit=80)
            payload = receipt.get("payload") or {}
            if any(token in kind.lower() for token in ("failed", "blocked", "error")):
                failure_kinds[kind] += 1
            if kind == "lead_synthesis_completed" and isinstance(payload, dict):
                findings = payload.get("findings", [])
                if isinstance(findings, list):
                    lessons.extend(_clean(item) for item in findings if _clean(item))

    repeated = [
        f"{kind} ×{count}"
        for kind, count in failure_kinds.items()
        if count >= 2
    ]
    return [
        f"- Recent Missions: {' | '.join(recent)}",
        f"- Mission Outcomes: {' | '.join(outcomes[:3])}",
        f"- Lessons Learned: {' | '.join(lessons[:3]) or _UNKNOWN}",
        f"- Reusable Patterns: {' | '.join(dict.fromkeys(patterns)) or _UNKNOWN}",
        (
            f"- Repeated Failures: {'; '.join(repeated)}"
            if repeated
            else "- Repeated Failures: none evidenced in current mission history"
        ),
    ]


def build_executive_context_blocks(
    *,
    workspace_id: str,
    pack: dict[str, Any],
) -> list[str]:
    """Project existing truth into VAXON's executive context; never invent gaps."""
    briefing = pack.get("briefing") or {}
    if not isinstance(briefing, dict):
        briefing = {}
    plans = _safe_recent_plans(workspace_id)
    presence = _safe_presence_settings()
    active_plan = next(
        (
            plan
            for plan in plans
            if _clean(plan.get("status"), limit=30)
            in {"active", "awaiting_engagement"}
        ),
        {},
    )
    next_actions = briefing.get("next_safe_actions") or []
    next_action = next_actions[0] if next_actions and isinstance(next_actions[0], dict) else {}
    top_signals = briefing.get("top_signals") or []
    top_signal = top_signals[0] if top_signals and isinstance(top_signals[0], dict) else {}
    autonomy_mode = _clean(presence.get("autonomy_mode"), limit=30) or "unknown"

    lines = [
        "ExecutiveIntent:",
        "- Vision: AXON-X is the single orchestration platform; VAXON is its embedded Executive Operating System.",
        f"- Current Milestone: {_first_text(active_plan.get('goal'))}",
        f"- Current Sprint: {_UNKNOWN}",
        (
            "- Current Priority: "
            + _first_text(
                briefing.get("advise"),
                next_action.get("title"),
                top_signal.get("title"),
            )
        ),
        f"- Known Risks: {_risk_line(briefing)}",
        "- Architectural Principles: reuse Lead and specialist seams; evidence before assumption; reversible delegation; no fabricated execution.",
        (
            "- Operator Preferences: "
            f"autonomy={autonomy_mode}; "
            f"voice_routing={_clean(presence.get('voice_routing_mode'), limit=40) or 'unknown'}; "
            f"persona_enabled={presence.get('operator_persona_enabled', 'unknown')}"
        ),
        f"- Current Constraints: {_constraint_line(briefing)}",
        f"- Decision Style: autonomy mode {autonomy_mode}; irreversible actions require Operator approval.",
        "MissionMemory:",
        *_mission_memory_lines(plans),
        "MissionSpecification contract (conversation artifact, every mission):",
        f"- Required fields: {_MISSION_FIELDS}.",
        "Evidence constitution:",
        f"- Allowed execution states: {_EVIDENCE_STATES}.",
        "- Never claim a later state from evidence of an earlier state; name the receipt or state gap.",
        "Delegation map:",
        "- Planner=Lead; Researcher=Watcher; React Dev=Frontend; Supabase Dev=Backend/Integrations; Verifier/GitHub=Watcher/Integrations.",
        "- Prefer Lead fan-out for multi-domain missions; use direct specialist routing only for clearly single-role work.",
    ]
    return lines


__all__ = ["build_executive_context_blocks"]
