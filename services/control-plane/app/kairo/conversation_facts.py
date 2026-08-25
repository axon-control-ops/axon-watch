"""DTO-grounded conversation facts for KAIRO replies."""

from __future__ import annotations

from typing import Any

from app.operator_briefing_signals import is_bootstrap_signal


def build_conversation_facts(pack: dict[str, Any]) -> dict[str, Any]:
    briefing = pack["briefing"]
    fleet = pack.get("fleet", {})
    recent_dialogue = [
        item
        for item in pack.get("recent_dialogue", [])
        if isinstance(item, dict) and str(item.get("content") or "").strip()
    ]
    top_signals = [
        item
        for item in briefing.get("top_signals", [])
        if isinstance(item, dict) and not is_bootstrap_signal(item)
    ]
    active_runs = [
        item for item in briefing.get("active_runs", []) if isinstance(item, dict)
    ]
    pending = int(briefing.get("pending_approvals", {}).get("count", 0))
    next_actions = [
        item for item in briefing.get("next_safe_actions", []) if isinstance(item, dict)
    ]
    top_signal = top_signals[0] if top_signals else {}
    primary_run = active_runs[0] if active_runs else {}
    review_ready_count = sum(
        1 for item in active_runs if str(item.get("phase") or "") == "review_ready"
    )
    dialogue_topic = ""
    for item in reversed(recent_dialogue):
        if str(item.get("role") or "").strip() == "operator":
            dialogue_topic = str(item.get("content") or "").strip()
            break
    if not dialogue_topic and recent_dialogue:
        dialogue_topic = str(recent_dialogue[-1].get("content") or "").strip()
    dialogue_topic = " ".join(dialogue_topic.split())
    if len(dialogue_topic) > 140:
        dialogue_topic = f"{dialogue_topic[:139].rstrip()}…"
    return {
        "pending_approvals": pending,
        "top_signal_title": str(top_signal.get("title", "")).strip(),
        "top_signal_summary": str(top_signal.get("summary", "")).strip(),
        "top_signal_severity": str(top_signal.get("severity", "")).strip(),
        "signal_count": len(top_signals),
        "active_run_count": len(active_runs),
        "review_ready_count": review_ready_count,
        "primary_run_summary": str(primary_run.get("summary", "")).strip(),
        "primary_run_phase": str(primary_run.get("phase", "")).strip(),
        "workspace_label": (
            str(pack.get("workspace", {}).get("display_name") or "").strip()
            or str(pack.get("workspace", {}).get("workspace_id") or "").strip()
        ),
        "notice": str(briefing.get("notice") or "").strip(),
        "advise": str(briefing.get("advise") or "").strip(),
        "degraded": bool(briefing.get("degraded", {}).get("active")),
        "watch_connected": bool(briefing.get("connectivity", {}).get("watch_connected")),
        "workspace_count": int(fleet.get("workspace_count", 0)),
        "critical_workspaces": int(fleet.get("critical_count", 0)),
        "attention_workspaces": int(fleet.get("attention_count", 0)),
        "next_action_title": str(next_actions[0].get("title", "")).strip() if next_actions else "",
        "scope_mode": str(briefing.get("scope", {}).get("mode", "fleet")),
        "cli_dispatch_ready": bool((briefing.get("cli_runtime") or {}).get("dispatch_ready", True)),
        "cli_blockers": [
            str(item).strip()
            for item in (briefing.get("cli_runtime") or {}).get("blockers", [])
            if str(item).strip()
        ],
        "recent_dialogue": recent_dialogue[-3:],
        "recent_dialogue_topic": dialogue_topic,
    }
