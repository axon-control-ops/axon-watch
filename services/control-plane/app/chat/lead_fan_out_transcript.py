"""Shared Lead fan-out / decompose transcript fence for AgentDock cards."""

from __future__ import annotations

import json
from typing import Any


def _assignment_rows(materialize: dict[str, Any], *, prefer_tasks: bool) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if prefer_tasks:
        for task in list(materialize.get("tasks") or []):
            if not isinstance(task, dict):
                continue
            role = str(task.get("owner_role") or "").strip() or "?"
            goal = " ".join(str(task.get("goal") or "").split())
            rows.append({"role": role, "goal": goal or "(no goal)"})
        if rows:
            return rows
    for run in list(materialize.get("runs") or []):
        if not isinstance(run, dict):
            continue
        role = str(run.get("owner_role") or "").strip() or "?"
        run_id = str(run.get("run_id") or "").strip()
        task_id = str(run.get("task_id") or "").strip()
        goal_bits = [bit for bit in (run_id and f"run {run_id}", task_id and f"task {task_id}") if bit]
        rows.append({"role": role, "goal": " · ".join(goal_bits) or "queued"})
    return rows


def format_lead_fan_out_agent_message(
    *,
    lead_name: str,
    materialize: dict[str, Any],
    mode: str,
    fleet_lines: list[str] | None = None,
    headline: str | None = None,
) -> str:
    """Persist a history-safe :::lead-fan-out fence + Confidence close-out."""
    plan_id = str(materialize.get("plan_id") or "").strip()
    runs = list(materialize.get("runs") or [])
    deferred = list(materialize.get("deferred") or [])
    cleaned_mode = str(mode or materialize.get("mode") or "decompose").strip().lower()
    prefer_tasks = cleaned_mode == "decompose"
    assignments = _assignment_rows(materialize, prefer_tasks=prefer_tasks)
    notes = [str(line).strip() for line in (fleet_lines or []) if str(line).strip()]
    payload = {
        "v": 1,
        "plan_id": plan_id,
        "mode": cleaned_mode,
        "lead_name": str(lead_name or "Lead").strip() or "Lead",
        "queued": len(runs),
        "deferred": len(deferred),
        "assignments": assignments,
        "notes": notes,
    }
    title = "Decomposed" if cleaned_mode == "decompose" else "Fan-out"
    opener = headline or (
        "Specialists are assigned — track them on the Task board and in each role thread."
        if cleaned_mode == "decompose"
        else "Specialists queued via Lead fan-out — continuous dispatch owns the starts."
    )
    fence = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # No trailing Confidence boilerplate: this is a deterministic fan-out
    # transcript, not an LLM turn — there's no model self-assessment to score.
    lines = [
        opener,
        "",
        f":::lead-fan-out {title}",
        fence,
        ":::",
        "",
        f"— {payload['lead_name']}",
    ]
    superseded = list(materialize.get("superseded_tasks") or [])
    if superseded:
        lines.insert(
            -1,
            f"Cleared {len(superseded)} overlapping stale queue task(s) so this handoff can move.",
        )
        lines.insert(-1, "")
    return "\n".join(lines)


__all__ = ["format_lead_fan_out_agent_message"]
