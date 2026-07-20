"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig
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


def build_continuous_worker_prompt(*, workspace_id: str, employee: EmployeeConfig) -> str:
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
    ci_clause = ""
    if role in {"watcher", "backend", "integrations"}:
        ci_clause = (
            " If git/working-tree or open PR changes are in your scope: "
            "(1) critically review the change for factual errors, missing steps, "
            "unsupported assumptions, and invented/unverified details; "
            "(2) rewrite the claim to be precise; end with Confidence: X/10; "
            "(3) only then run local verify (`npm run verify:contracts` and targeted tests) "
            "and report the real command output. "
            "Never report FAILED without the exact failing check, file, and error text. "
        )
    memory_clause = (
        " Memory safety: do NOT start DashPro `web:dev` / Expo / Metro / "
        "`typecheck` with large NODE_OPTIONS heaps unless the operator explicitly asked. "
        "Prefer editing + targeted tests. Never launch a second heavy server if one is "
        "already listening. Axon-X operator UI is :4173 — do not start legacy :7734. "
    )
    prior_failure = _prior_failure_clause(workspace_id=workspace_id, role=role)
    return (
        f"{identity} "
        f"This is a bounded continuous shift ({schedule}). "
        f"{prior_failure}"
        "Inspect the workspace, pick the highest-value in-scope task, do it with receipts, "
        "and summarize what changed. Stay inside your role boundary."
        f"{ci_clause}"
        f"{memory_clause}"
        " If a step fails, say what failed and why (command, assertion, import, CI step) — "
        "never a bare FAILED."
    )
