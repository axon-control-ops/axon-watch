"""Create/lease a CI repair task and one-shot dispatch a continuous worker."""

from __future__ import annotations

import logging
import threading
from typing import Any

from app.ci_remediation.config import CiRemediationBinding
from app.persistence import task_store
from app.runs.service import RunLifecycleError, append_run_execution_receipt, create_run
from app.workspace_agents.config_loader import (
    EmployeeConfig,
    load_workspace_agent_configs,
)
from app.workspace_agents.worker_dispatch import (
    dispatch_continuous_worker_run,
    worker_dispatch_enabled,
)

logger = logging.getLogger(__name__)


def _employee_for_role(workspace_id: str, role: str) -> EmployeeConfig | None:
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    company = companies.get(workspace_id)
    if company is None:
        return None
    for employee in company.employees:
        if str(employee.role or "").strip().lower() == role and employee.enabled:
            return employee
    return None


def build_repair_goal(
    classified: dict[str, str],
    binding: CiRemediationBinding,
    *,
    dedupe_key: str,
) -> str:
    workflow = classified["workflow_name"]
    branch = classified.get("head_branch") or "unknown-branch"
    run_url = classified.get("html_url") or ""
    failing = classified.get("failing_step") or "unknown failing step"
    return (
        f"CI repair: {workflow} failed on {branch}. "
        f"Failing step hint: {failing}. "
        f"Checkout the exact failing head `{classified.get('head_sha') or 'HEAD'}` "
        f"on branch `{branch}` (fast-forward only; never force-push). "
        f"Use `gh run view {classified['run_id']} --log-failed`, apply the smallest fix "
        f"(often scripts/guardrails/hotspot_budgets.json or extraction), commit, "
        f"push per push_policy={binding.push_policy} (draft PR; no protected merge/"
        f"force-push), then watch the repair-head run and report its URL + conclusion. "
        f"Source run: {run_url or classified['run_id']}. "
        f"CI remediation dedupe_key: {dedupe_key}."
    )


def build_acceptance(classified: dict[str, str], binding: CiRemediationBinding) -> str:
    return (
        f"{classified['workflow_name']} green on the repair head OR a draft PR URL "
        f"with a clear blocker after at most {binding.attempt_budget} attempts; "
        "never merge protected branches; include Critical Review Confidence."
    )


def repair_goal_match_key(classified: dict[str, str]) -> str:
    workflow = str(classified.get("workflow_name") or "").strip()
    branch = str(classified.get("head_branch") or "unknown-branch").strip()
    return f"CI repair: {workflow} failed on {branch}"


def supersede_prior_repair_tasks(
    *,
    workspace_id: str,
    classified: dict[str, str],
    keep_task_id: str | None = None,
) -> list[dict[str, Any]]:
    """Finalize older open/leased repair tasks for the same workflow+branch."""
    needle = repair_goal_match_key(classified)
    return task_store.cancel_tasks_matching_goal_prefix(
        workspace_id=workspace_id,
        goal_substr=needle,
        exclude_task_id=keep_task_id,
        terminal_outcome="superseded by newer CI repair head",
    )


def _park_repair_under_ship_plan(
    *,
    binding: CiRemediationBinding,
    classified: dict[str, str],
    dedupe_key: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Open a Lead finding instead of leasing Watcher under an active ship plan."""
    from app.workspace_agents.lead_plan_control import plan_marker
    from app.workspace_agents.lead_text import truncate_text

    plan_id = str(plan.get("plan_id") or "").strip()
    plan_goal = truncate_text(str(plan.get("goal") or ""), max_len=160) or "Lead plan"
    workflow = classified.get("workflow_name") or "CI"
    branch = classified.get("head_branch") or "unknown-branch"
    run_url = classified.get("html_url") or classified.get("run_id") or ""
    failing = classified.get("failing_step") or "unknown failing step"
    marker = plan_marker(plan_id)

    # Collapse onto any open/leased Lead sticky ticket for this plan — do not
    # spawn a second Lead lease beside an existing "advance [plan …]" follow-up.
    needle = repair_goal_match_key(classified)
    existing: dict[str, Any] | None = None
    for status in ("open", "leased"):
        for row in task_store.list_tasks(
            workspace_id=binding.workspace_id,
            status=status,
            limit=100,
        ):
            if str(row.get("owner_role") or "").strip().lower() != "lead":
                continue
            goal = str(row.get("goal") or "")
            if marker and marker in goal:
                existing = dict(row)
                break
        if existing is not None:
            break

    superseded = supersede_prior_repair_tasks(
        workspace_id=binding.workspace_id,
        classified=classified,
    )
    if superseded:
        logger.info(
            "CI remediation superseded %s prior repair task(s) for %s (parked)",
            len(superseded),
            needle,
        )

    reused_sticky = existing is not None
    if existing is None:
        existing = task_store.create_task(
            workspace_id=binding.workspace_id,
            goal=(
                f'Lead: advance "{plan_goal}" toward Done {marker} — '
                f"CI finding: {needle}. Failing step: {failing}. "
                f"Source: {run_url}. dedupe_key: {dedupe_key}."
            ),
            acceptance_criteria=(
                f"Sole truth: advance plan {plan_id} — {plan_goal}. "
                f"Treat {workflow} on {branch} as a blocker input, not a parallel Watcher dig. "
                "Decide whether to assign a specialist under the plan, escalate Decide, "
                "or defer non-blocking CI. End with Confidence: N/10."
            ),
            risk="normal",
            owner_role="lead",
            attempt_budget=2,
        )

    try:
        from app.workspace_agents import lead_plan_store

        lead_plan_store.append_receipt(
            plan_id=plan_id,
            workspace_id=binding.workspace_id,
            kind="ci_finding_parked",
            payload={
                "task_id": existing.get("task_id"),
                "workflow_name": workflow,
                "head_branch": branch,
                "run_id": classified.get("run_id"),
                "html_url": classified.get("html_url"),
                "failing_step": failing,
                "dedupe_key": dedupe_key,
                "reused_sticky_lead_task": reused_sticky,
            },
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("ci finding plan receipt failed: %s", exc)
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(
            receipt_id=f"ci_parked_{plan_id}_{classified.get('run_id') or dedupe_key}"
        )
    except Exception:  # noqa: BLE001
        pass

    parked = dict(existing)
    parked["parked_under_plan"] = plan_id
    logger.info(
        "CI remediation parked under ship plan %s workspace=%s workflow=%s task=%s",
        plan_id,
        binding.workspace_id,
        workflow,
        parked.get("task_id"),
    )
    return parked


def create_and_lease_repair_task(
    *,
    binding: CiRemediationBinding,
    classified: dict[str, str],
    dedupe_key: str,
    owner_role: str | None = None,
) -> dict[str, Any]:
    from app.workspace_agents.lead_plan_control import controlling_ship_plan

    ship_plan = controlling_ship_plan(binding.workspace_id)
    if ship_plan is not None:
        return _park_repair_under_ship_plan(
            binding=binding,
            classified=classified,
            dedupe_key=dedupe_key,
            plan=ship_plan,
        )

    role = (owner_role or binding.owner_role).strip().lower() or "watcher"
    superseded = supersede_prior_repair_tasks(
        workspace_id=binding.workspace_id,
        classified=classified,
    )
    if superseded:
        logger.info(
            "CI remediation superseded %s prior repair task(s) for %s",
            len(superseded),
            repair_goal_match_key(classified),
        )
    opened = task_store.create_task(
        workspace_id=binding.workspace_id,
        goal=build_repair_goal(classified, binding, dedupe_key=dedupe_key),
        acceptance_criteria=build_acceptance(classified, binding),
        risk="normal",
        owner_role=role,
        attempt_budget=binding.attempt_budget,
    )
    holder = f"ci-remediation-{binding.workspace_id}-{role}"
    return task_store.lease_task(str(opened["task_id"]), lease_holder=holder)


def _dispatch_thread(
    *,
    workspace_id: str,
    employee: EmployeeConfig,
    run_record: dict[str, Any],
) -> None:
    try:
        dispatch_continuous_worker_run(
            workspace_id=workspace_id,
            employee=employee,
            run_record=run_record,
        )
    except Exception:  # noqa: BLE001 — never crash webhook thread
        logger.exception(
            "CI remediation dispatch failed for run %s",
            run_record.get("run_id"),
        )


def dispatch_repair_run(
    *,
    binding: CiRemediationBinding,
    leased_task: dict[str, Any],
    classified: dict[str, str],
) -> dict[str, Any] | None:
    role = str(leased_task.get("owner_role") or binding.owner_role).strip().lower()
    employee = _employee_for_role(binding.workspace_id, role)
    if employee is None:
        logger.warning(
            "CI remediation: no employee for role=%s workspace=%s",
            role,
            binding.workspace_id,
        )
        return None
    task_id = str(leased_task.get("task_id") or "").strip()
    name = str(employee.name or role).strip() or role
    try:
        run = create_run(
            workspace_id=binding.workspace_id,
            mode="agent",
            summary=f"{name}: CI repair {classified.get('workflow_name', '')}"[:120],
            detail=(
                f"Gate 9 CI remediation for {classified.get('workflow_name')} "
                f"run={classified.get('run_id')} task={task_id}"
            ),
            employee_role=role,
            task_id=task_id,
            require_leased_task=True,
            requires_approval=False,
        )
    except RunLifecycleError as exc:
        logger.warning("CI remediation create_run refused: %s", exc)
        try:
            task_store.fail_task(
                task_id,
                terminal_outcome=f"create_run refused: {exc}",
                reopen_if_budget_remaining=True,
            )
        except task_store.TaskLedgerError:
            logger.exception("could not reopen CI repair task %s", task_id)
        return None

    append_run_execution_receipt(
        str(run["run_id"]),
        receipt_type="ci_remediation_assigned",
        receipt_summary=(
            f"Gate 9 assigned {role} to repair {classified.get('workflow_name')} "
            f"run {classified.get('run_id')}"
        ),
        actor="ci_remediation",
    )
    if binding.dispatch_on_ingest and worker_dispatch_enabled():
        threading.Thread(
            target=_dispatch_thread,
            kwargs={
                "workspace_id": binding.workspace_id,
                "employee": employee,
                "run_record": run,
            },
            daemon=True,
            name=f"ci-repair-dispatch-{run.get('run_id')}",
        ).start()
    return run
