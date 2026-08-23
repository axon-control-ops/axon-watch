"""Create/lease a fleet-repair task and one-shot dispatch a continuous worker.

Mirrors app/ci_remediation/dispatch_repair.py's shape closely — same
task_store + continuous-worker pipeline, same supersede/attempt-budget loop
guard. The one structural difference: dispatch always targets
config.target_workspace_id (axon-watch's own repo), never the workspace that
observed the failure — see classify.py/detect.py module docstrings for why.
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

from app.fleet_self_heal.config import FleetSelfHealConfig
from app.persistence import task_store
from app.runs.service import RunLifecycleError, append_run_execution_receipt, create_run
from app.workspace_agents.config_loader import EmployeeConfig, load_workspace_agent_configs
from app.workspace_agents.worker_dispatch import (
    dispatch_continuous_worker_run,
    worker_dispatch_enabled,
)

from app.fleet_self_heal import store

logger = logging.getLogger(__name__)

GOAL_PREFIX = "VAXON fleet repair"


def _employee_for_role(workspace_id: str, role: str) -> EmployeeConfig | None:
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    company = companies.get(workspace_id)
    if company is None:
        return None
    for employee in company.employees:
        if str(employee.role or "").strip().lower() == role and employee.enabled:
            return employee
    return None


def repair_goal_match_key(fingerprint: str) -> str:
    return f"{GOAL_PREFIX} [{fingerprint}]"


def build_repair_goal(event: dict[str, Any], *, fingerprint: str) -> str:
    run_ids = ", ".join(event.get("sample_run_ids_json") or [])
    workspaces = event.get("workspaces_json") or []
    roles = event.get("roles_json") or []
    pairs = ", ".join(f"{w}:{r}" for w, r in zip(workspaces, roles))
    base = (
        f"{repair_goal_match_key(fingerprint)}: {event.get('subsystem', 'unknown subsystem')} "
        f"failures across the agent fleet (occurrences={event.get('occurrence_count', 0)}). "
        f"Affected run_ids: {run_ids or 'none recorded'}. "
        f"Affected workspace:role pairs: {pairs or 'none recorded'}. "
    )
    file_hint = str(event.get("file_hint") or "")
    if file_hint:
        base += f"Likely source: {file_hint}. "
    base += (
        "Reproduce by querying run_store history for this failure signature "
        "(app/persistence/run_store.py::list_history against the run_ids above), "
        "read the dispatch/sandbox/runtime code the traceback points at, and "
        "reproduce against the real sandbox/CLI binaries before patching — "
        "do not guess at a fix from the error string alone."
    )
    if event.get("status") == "regressed":
        base += (
            f" REGRESSION: this exact signature was already verified fixed in "
            f"commit {event.get('resolution_commit_ref')} on "
            f"{event.get('resolution_verified_at')}. The prior fix did not hold — "
            "investigate why (reverted? incomplete? new code path?) before writing "
            "a new patch; do not just resubmit the same diff."
        )
    return base


def build_acceptance(event: dict[str, Any], *, config: FleetSelfHealConfig) -> str:
    return (
        "Root-cause the fleet-infra bug (not a symptom patch). "
        "Add or extend a regression test under tests/ that reproduces this exact "
        "failure signature and fails without your fix (mirror "
        "tests/test_cursor_agent_recursion_retry.py style) — a fix without a "
        "regression test is not acceptable. "
        "Push to a throwaway branch (never dev/master directly), open a draft PR, "
        f"then confirm a green Axon-X Fast Gate run on that head (push_policy="
        f"{config.push_policy}) before reporting success — a red Fast Gate is not "
        "a completed repair. Never force-push or merge protected branches. "
        "Report outcome to POST /api/fleet-self-heal/report-outcome with "
        f"fingerprint={event.get('fingerprint', '')}, success, commit_ref (the fix "
        "commit sha or PR URL), and detail. End with Confidence: N/10."
    )


def supersede_prior_repair_tasks(*, workspace_id: str, fingerprint: str) -> list[dict[str, Any]]:
    """Finalize older open/leased repair tasks for the same fingerprint."""
    return task_store.cancel_tasks_matching_goal_prefix(
        workspace_id=workspace_id,
        goal_substr=repair_goal_match_key(fingerprint),
        terminal_outcome="superseded by newer VAXON fleet-repair dispatch",
    )


def _park_under_ship_plan(
    *,
    config: FleetSelfHealConfig,
    event: dict[str, Any],
    fingerprint: str,
    plan: dict[str, Any],
) -> dict[str, Any]:
    """Open a Lead finding instead of leasing a specialist under an active ship plan."""
    from app.workspace_agents.lead_plan_control import plan_marker
    from app.workspace_agents.lead_text import truncate_text

    workspace_id = config.target_workspace_id
    plan_id = str(plan.get("plan_id") or "").strip()
    plan_goal = truncate_text(str(plan.get("goal") or ""), max_len=160) or "Lead plan"
    marker = plan_marker(plan_id)
    needle = repair_goal_match_key(fingerprint)

    existing: dict[str, Any] | None = None
    for status in ("open", "leased"):
        for row in task_store.list_tasks(workspace_id=workspace_id, status=status, limit=100):
            if str(row.get("owner_role") or "").strip().lower() != "lead":
                continue
            goal = str(row.get("goal") or "")
            if marker and marker in goal:
                existing = dict(row)
                break
        if existing is not None:
            break

    superseded = supersede_prior_repair_tasks(workspace_id=workspace_id, fingerprint=fingerprint)
    if superseded:
        logger.info("VAXON fleet repair superseded %s prior task(s) for %s (parked)", len(superseded), needle)

    reused_sticky = existing is not None
    if existing is None:
        existing = task_store.create_task(
            workspace_id=workspace_id,
            goal=(
                f'Lead: advance "{plan_goal}" toward Done {marker} — '
                f"VAXON fleet finding: {needle}. Subsystem: {event.get('subsystem')}."
            ),
            acceptance_criteria=(
                f"Sole truth: advance plan {plan_id} — {plan_goal}. "
                f"Treat the fleet-infra bug {fingerprint} as a blocker input, not a "
                "parallel Watcher dig. Decide whether to assign a specialist under "
                "the plan, escalate Decide, or defer non-blocking repair. "
                "End with Confidence: N/10."
            ),
            risk="normal",
            owner_role="lead",
            attempt_budget=2,
        )

    parked = dict(existing)
    parked["parked_under_plan"] = plan_id
    store.attach_task(fingerprint, str(parked.get("task_id") or ""), status="repairing")

    try:
        from app.workspace_agents import lead_plan_store

        lead_plan_store.append_receipt(
            plan_id=plan_id,
            workspace_id=workspace_id,
            kind="fleet_repair_finding_parked",
            payload={
                "task_id": parked.get("task_id"),
                "fingerprint": fingerprint,
                "subsystem": event.get("subsystem"),
                "file_hint": event.get("file_hint"),
                "occurrence_count": event.get("occurrence_count"),
                "reused_sticky_lead_task": reused_sticky,
            },
        )
    except Exception as exc:  # noqa: BLE001 — a missing audit receipt must not block parking
        logger.warning("VAXON fleet repair finding plan receipt failed: %s", exc)
    try:
        from app.live_events import broadcast_material_change

        broadcast_material_change(receipt_id=f"fleet_repair_parked_{plan_id}_{fingerprint}")
    except Exception:  # noqa: BLE001 — live-update push must not block parking
        pass

    logger.info(
        "VAXON fleet repair parked under ship plan %s workspace=%s fingerprint=%s task=%s",
        plan_id, workspace_id, fingerprint, parked.get("task_id"),
    )
    return parked


def create_and_lease_repair_task(
    *, config: FleetSelfHealConfig, event: dict[str, Any], fingerprint: str,
) -> dict[str, Any]:
    from app.workspace_agents.lead_plan_control import controlling_ship_plan

    workspace_id = config.target_workspace_id  # always axon-watch's own repo
    ship_plan = controlling_ship_plan(workspace_id)
    if ship_plan is not None:
        return _park_under_ship_plan(config=config, event=event, fingerprint=fingerprint, plan=ship_plan)

    role = config.role_for_subsystem(str(event.get("subsystem") or ""))
    superseded = supersede_prior_repair_tasks(workspace_id=workspace_id, fingerprint=fingerprint)
    if superseded:
        logger.info(
            "VAXON fleet repair superseded %s prior task(s) for %s",
            len(superseded), repair_goal_match_key(fingerprint),
        )
    opened = task_store.create_task(
        workspace_id=workspace_id,
        goal=build_repair_goal(event, fingerprint=fingerprint),
        acceptance_criteria=build_acceptance(event, config=config),
        risk="normal",
        owner_role=role,
        attempt_budget=config.attempt_budget_per_dispatch,
    )
    leased = task_store.lease_task(
        str(opened["task_id"]), lease_holder=f"vaxon-fleet-repair-{fingerprint}"
    )
    store.attach_task(fingerprint, str(leased.get("task_id") or ""), status="repairing")
    return leased


def _dispatch_thread(*, workspace_id: str, employee: EmployeeConfig, run_record: dict[str, Any]) -> None:
    try:
        dispatch_continuous_worker_run(workspace_id=workspace_id, employee=employee, run_record=run_record)
    except Exception:  # noqa: BLE001 — never crash the scheduler thread
        logger.exception("VAXON fleet repair dispatch failed for run %s", run_record.get("run_id"))


def dispatch_repair_run(
    *, config: FleetSelfHealConfig, leased_task: dict[str, Any], fingerprint: str,
) -> dict[str, Any] | None:
    workspace_id = config.target_workspace_id
    role = str(leased_task.get("owner_role") or config.owner_role).strip().lower()
    employee = _employee_for_role(workspace_id, role)
    if employee is None:
        logger.warning("VAXON fleet repair: no employee for role=%s workspace=%s", role, workspace_id)
        return None
    task_id = str(leased_task.get("task_id") or "").strip()
    name = str(employee.name or role).strip() or role
    try:
        run = create_run(
            workspace_id=workspace_id,
            mode="agent",
            summary=f"{name}: VAXON fleet repair {fingerprint}"[:120],
            detail=f"VAXON fleet self-heal repair for fingerprint={fingerprint} task={task_id}",
            employee_role=role,
            task_id=task_id,
            require_leased_task=True,
            requires_approval=False,
        )
    except RunLifecycleError as exc:
        logger.warning("VAXON fleet repair create_run refused: %s", exc)
        try:
            task_store.fail_task(
                task_id, terminal_outcome=f"create_run refused: {exc}", reopen_if_budget_remaining=True,
            )
        except task_store.TaskLedgerError:
            logger.exception("could not reopen VAXON fleet repair task %s", task_id)
        return None

    append_run_execution_receipt(
        str(run["run_id"]),
        receipt_type="fleet_self_heal_assigned",
        receipt_summary=f"VAXON fleet self-heal assigned {role} to repair {fingerprint}",
        actor="fleet_self_heal",
    )
    if worker_dispatch_enabled():
        threading.Thread(
            target=_dispatch_thread,
            kwargs={"workspace_id": workspace_id, "employee": employee, "run_record": run},
            daemon=True,
            name=f"vaxon-fleet-repair-dispatch-{run.get('run_id')}",
        ).start()
    return run


def dispatch_dispatchable_fingerprints(
    *, config: FleetSelfHealConfig, fingerprints: list[str],
) -> list[dict[str, Any]]:
    """Entry point for detect.py's dispatchable list — create+lease+dispatch each."""
    if not config.dispatch_enabled:
        logger.info(
            "VAXON fleet repair dry-run: would dispatch %s fingerprint(s): %s",
            len(fingerprints), json.dumps(fingerprints),
        )
        return []
    dispatched: list[dict[str, Any]] = []
    for fingerprint in fingerprints:
        event = store.get_event(fingerprint)
        if event is None:
            continue
        leased = create_and_lease_repair_task(config=config, event=event, fingerprint=fingerprint)
        if leased.get("parked_under_plan"):
            dispatched.append(leased)
            continue
        run = dispatch_repair_run(config=config, leased_task=leased, fingerprint=fingerprint)
        if run is not None:
            dispatched.append(run)
    return dispatched


__all__ = [
    "GOAL_PREFIX",
    "build_acceptance",
    "build_repair_goal",
    "create_and_lease_repair_task",
    "dispatch_dispatchable_fingerprints",
    "dispatch_repair_run",
    "repair_goal_match_key",
    "supersede_prior_repair_tasks",
]
