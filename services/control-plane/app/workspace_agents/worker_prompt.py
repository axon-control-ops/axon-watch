"""Role-scoped prompts for continuous employee-agent shifts."""

from __future__ import annotations

import re
from typing import Any

from app.workspace_agents.catalog import _DEFAULT_OWNS
from app.workspace_agents.config_loader import EmployeeConfig
from app.workspace_agents.critical_review_clause import append_critical_review_clause
from app.workspace_agents.employee_persona_prompt import build_employee_identity_line
from app.workspace_agents.run_outcome import latest_role_run_outcome
from app.workspace_agents.team_roster_context import build_team_roster_context

OUT_OF_SCOPE_GUARD_MARKER = "OUT_OF_SCOPE_GUARD:"
_OUT_OF_SCOPE_GUARD_RE = re.compile(r"OUT_OF_SCOPE_GUARD:\s*(.+)", re.IGNORECASE)


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


def _task_scope_anchors(*parts: str, limit: int = 8) -> list[str]:
    anchors: list[str] = []
    seen: set[str] = set()
    for part in parts:
        text = str(part or "")
        candidates = re.findall(r"`([^`]+)`", text)
        candidates.extend(re.findall(r"\b[\w./-]*[./_-][\w./-]+\b", text))
        for raw in candidates:
            cleaned = str(raw).strip().strip(".,;:()[]{}")
            if not cleaned or len(cleaned) < 3:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            anchors.append(cleaned)
            if len(anchors) >= limit:
                return anchors
    return anchors


def _task_scope_clause(
    *,
    goal: str,
    acceptance: str,
    allowed_paths: list[str] | None = None,
) -> str:
    paths = [str(p).strip() for p in (allowed_paths or []) if str(p).strip()]
    anchors = _task_scope_anchors(goal, acceptance)
    anchor_clause = ""
    if paths:
        joined = ", ".join(f"`{path}`" for path in paths[:12])
        anchor_clause = (
            f" Explicit allowed write paths for this leased task: {joined}. "
            "Do not modify any path outside that allowlist."
        )
    elif anchors:
        joined = ", ".join(f"`{anchor}`" for anchor in anchors)
        anchor_clause = f" Hard scope anchors from the task: {joined}. "
    return (
        " Scope guard: before you browse, edit, or summarize anything, lock onto the "
        "leased task's exact goal and acceptance criteria."
        f"{anchor_clause}"
        "Only open, mention, or modify files and topics that directly serve that scope. "
        "Do not drift into neighboring files, similarly named campaigns, prior tasks, or "
        "semantically related artifacts just because they are nearby. "
        "If the goal is about a README, docs, layout, bug, API, or specific deliverable, "
        "treat unrelated posts, assets, illustrations, marketing copy, and old workspace "
        "tasks as out of scope unless the goal explicitly asks for them. "
        f"If the next file or topic is not clearly justified by the task, stop and reply "
        f"with `{OUT_OF_SCOPE_GUARD_MARKER} <file-or-topic> is not required for this leased task` "
        "instead of continuing."
    )


def parse_out_of_scope_guard(reply_text: str) -> str | None:
    match = _OUT_OF_SCOPE_GUARD_RE.search(str(reply_text or ""))
    if match is None:
        return None
    detail = " ".join(match.group(1).split()).strip()
    return detail or "out-of-scope guard triggered"


def build_continuous_worker_prompt(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    task: dict[str, Any] | None = None,
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
    task_payload = task if isinstance(task, dict) else {}
    task_id = str(task_payload.get("task_id") or "").strip() or "task-unspecified"
    goal = str(task_payload.get("goal") or "").strip() or "Complete the leased task"
    acceptance = str(task_payload.get("acceptance_criteria") or "").strip()
    acceptance_clause = (
        f" Acceptance criteria: {acceptance}."
        if acceptance
        else " Use receipts to prove the goal is met."
    )
    allowed_paths_raw = task_payload.get("allowed_paths")
    allowed_paths = (
        [str(item).strip() for item in allowed_paths_raw if str(item).strip()]
        if isinstance(allowed_paths_raw, list)
        else []
    )
    scope_clause = _task_scope_clause(
        goal=goal,
        acceptance=acceptance,
        allowed_paths=allowed_paths,
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
    if workspace_id.strip() == "workspace_axon_watch" and role in {"watcher", "integrations", "lead"}:
        ci_clause += (
            " After any push to origin for this repo, poll Axon-X Fast Gate "
            "(`./scripts/ops/watch-fast-gate.sh` or `gh run watch`) and report the "
            "run URL + conclusion. Fix file-size ratchet failures via "
            "`scripts/guardrails/hotspot_budgets.json` or extraction — do not ignore red CI. "
        )
    goal_l = goal.lower()
    if "ci repair:" in goal_l or "gate 9" in goal_l or "fast gate" in goal_l:
        ci_clause += (
            " This leased task is a Gate 9 CI remediation. "
            "1) `gh run view <run_id> --log-failed` for the first hard-fail step. "
            "2) Apply the smallest fix (ratchet/extract/type). "
            "3) Commit and open/update a draft PR (push_policy=draft_pr); "
            "never force-push or merge protected branches. "
            "4) Re-watch the exact workflow on the repair head. "
            "5) POST JSON to "
            "`http://127.0.0.1:8787/api/ci-remediation/report-outcome` with the "
            "dedupe_key from the task goal, workspace_id, workflow_name, head_branch, "
            "success true/false, detail, html_url, and draft_pr_url. Include "
            "`Authorization: Bearer $AXON_WATCH_OPERATOR_TOKEN` when configured. "
            "Report spoken-ready outcome for the unaware operator. "
        )
    memory_clause = (
        " Memory safety: do NOT start DashPro `web:dev` / Expo / Metro / "
        "`typecheck` with large NODE_OPTIONS heaps unless the operator explicitly asked. "
        "Prefer editing + targeted tests. Never launch a second heavy server if one is "
        "already listening. Axon-X operator UI is :4173 — do not start legacy :7734. "
        "Long-running OTA/Expo/EAS jobs: start once and wait for that shell tool; do not "
        "busy-poll with repeated shell probes every few seconds — check sparsely (~30–60s). "
    )
    prior_failure = _prior_failure_clause(workspace_id=workspace_id, role=role)
    roster_block = build_team_roster_context(workspace_id, viewer_role=role)
    roster_clause = f"\n\n{roster_block}" if roster_block else ""
    lead_clause = ""
    if role == "lead":
        lead_clause = (
            " As Lead, treat the company team roster block as authoritative for "
            "teammates, roles, and owns — do not Glob/Grep/Read the tree to discover "
            "staffing before planning or delegating."
        )
    return append_critical_review_clause(
        f"{identity} "
        f"This is a bounded continuous shift ({schedule}) for leased task {task_id}. "
        f"{prior_failure}"
        f"Execute only this leased task — do not invent or self-select other work. "
        f"Goal: {goal}.{acceptance_clause} "
        "Do it with receipts and summarize what changed. Stay inside your role boundary."
        f"{scope_clause}"
        f"{lead_clause}"
        f"{ci_clause}"
        f"{memory_clause}"
        " If a step fails, say what failed and why (command, assertion, import, CI step) — "
        "never a bare FAILED."
        f"{roster_clause}"
    )
