"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig


def build_continuous_worker_prompt(*, workspace_id: str, employee: EmployeeConfig) -> str:
    role = str(employee.role or "").strip().lower() or "workspace_agent"
    owns = str(employee.owns or "").strip() or _DEFAULT_OWNS.get(role, "assigned workspace work")
    name = str(employee.name or role).strip() or role
    schedule = str(employee.schedule or "continuous").strip().lower()
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
    return (
        f"You are {name}, the {role} employee for workspace {workspace_id}. "
        f"You own: {owns}. "
        f"This is a bounded continuous shift ({schedule}). "
        "Inspect the workspace, pick the highest-value in-scope task, do it with receipts, "
        "and summarize what changed. Stay inside your role boundary."
        f"{ci_clause}"
        " If a step fails, say what failed and why (command, assertion, import, CI step) — "
        "never a bare FAILED."
    )
