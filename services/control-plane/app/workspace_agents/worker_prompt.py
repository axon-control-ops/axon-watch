"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

from typing import Any

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.critical_review_clause import append_critical_review_clause
from app.workspace_agents.employee_persona_prompt import build_employee_identity_line
from app.workspace_agents.run_outcome import latest_role_run_outcome


def _prior_failure_clause(*, workspace_id: str, role: str) -> str:
    """Surface the last terminal failure so a new shift can retry with context."""
    outcome = latest_role_run_outcome(workspace_id, role)
    if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
        return ""
    detail = str(outcome.get("detail") or "").strip()
    run_id = str(outcome.get("run_id") or "").strip()
    if not detail:
        detail = "open run history for receipts"
    run_hint = f" (run {run_id})" if run_id else ""
    return (
        f" Prior shift failed{run_hint}: {detail}. "
        "Prefer fixing or clearing that failure before unrelated work. "
    )


def build_continuous_worker_prompt(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    task: dict[str, Any],
) -> str:
    role = str(employee.role or "").strip().lower() or "workspace_agent"
    owns = str(employee.owns or "").strip() or _DEFAULT_OWNS.get(role, "assigned workspace work")
    name = str(employee.name or role).strip() or role
    schedule = str(employee.schedule or "continuous").strip().lower()
    identity = build_employee_identity_line(
        workspace_id=workspace_id,
        name=name,
        role=role,
        owns=owns,
    )
    task_id = str(task.get("task_id") or "").strip() or "unknown-task"
    goal = str(task.get("goal") or "").strip() or "Complete the leased task"
    acceptance = str(task.get("acceptance_criteria") or "").strip()
    acceptance_clause = (
        f" Acceptance criteria: {acceptance}."
        if acceptance
        else " Use receipts to prove the goal is met."
    )
    ci_clause = ""
    if role in {"watcher", "backend", "integrations"}:
        ci_clause = (
            " If git/working-tree or open PR changes are in your scope: "
            "after the Critical Review Clause rewrite, run local verify "
            "(`npm run verify:contracts` and targeted tests) and report the real "
            "command output. "
            "Never report FAILED without the exact failing check, file, and error text. "
        )
    memory_clause = (
        " Memory safety: do NOT start DashPro `web:dev` / Expo / Metro / "
        "`typecheck` with large NODE_OPTIONS heaps unless the operator explicitly asked. "
        "Prefer editing + targeted tests. Never launch a second heavy server if one is "
        "already listening. Axon-X operator UI is :4173 — do not start legacy :7734. "
    )
    prior_failure = _prior_failure_clause(workspace_id=workspace_id, role=role)
    return append_critical_review_clause(
        f"{identity} "
        f"This is a bounded continuous shift ({schedule}) for leased task {task_id}. "
        f"{prior_failure}"
        f"Execute only this leased task — do not invent or self-select other work. "
        f"Goal: {goal}.{acceptance_clause} "
        "Do it with receipts and summarize what changed. Stay inside your role boundary."
        f"{ci_clause}"
        f"{memory_clause}"
        " If a step fails, say what failed and why (command, assertion, import, CI step) — "
        "never a bare FAILED."
    )
