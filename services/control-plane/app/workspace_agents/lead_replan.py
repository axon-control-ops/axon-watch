"""Receipt-backed Lead replans and deterministic specialist synthesis (Gate 5)."""

from __future__ import annotations

from typing import Any

from app.persistence import task_store
from app.runs.service import RunLifecycleError, RunNotFoundError, stop_run
from app.workspace_agents import lead_plan_store
from app.workspace_agents.lead_fan_out import materialize_lead_fan_out
from app.workspace_agents.lead_task_plan import PlanMode

_TERMINAL_TASK_STATUSES = frozenset({"completed", "failed", "cancelled"})
_ACTIVE_SYNTH_PLAN_STATUSES = frozenset({"active", "completed", "awaiting_engagement"})


class LeadReplanError(ValueError):
    """Raised when an explicit replan or synthesis cannot be completed."""


def _plan_tasks(plan_id: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for link in lead_plan_store.plan_task_links(plan_id):
        task = task_store.get_task(link["task_id"])
        if task is not None:
            tasks.append({**task, "plan_key": link["plan_key"]})
    return tasks


def _roster_name_for_role(workspace_id: str, role: str) -> str:
    from app.workspace_agents import build_company_roster

    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return ""
    want = role.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == want:
            return str(row.get("name") or "").strip()
    return ""


def _specialist_reply_excerpt(workspace_id: str, run_id: str, *, max_len: int = 400) -> str:
    from app.persistence import chat_store

    cleaned_run = str(run_id or "").strip()
    if not cleaned_run:
        return ""
    for thread in chat_store.list_threads_for_workspace(workspace_id, thread_kind="ide", limit=50):
        thread_id = str(thread.get("thread_id") or "").strip()
        if not thread_id:
            continue
        try:
            history = chat_store.list_thread_messages(thread_id)
        except Exception:
            continue
        for message in reversed(history or []):
            if str(message.get("run_id") or "").strip() != cleaned_run:
                continue
            if str(message.get("role") or "").strip() != "agent":
                continue
            text = " ".join(str(message.get("content") or "").split())
            if not text:
                continue
            # Prefer the conversational report after thinking blocks when present.
            if ":::thinking" in text and ":::" in text[12:]:
                parts = text.split(":::")
                # take last non-empty non-thinking segment
                for part in reversed(parts):
                    cleaned = part.strip()
                    if cleaned and not cleaned.startswith("thinking") and not cleaned.startswith("tool"):
                        text = cleaned
                        break
            if len(text) > max_len:
                return f"{text[: max_len - 1].rstrip()}…"
            return text
    return ""


def _build_synthesis_findings(
    *,
    workspace_id: str,
    tasks: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    from app.persistence import run_store

    runs_by_task: dict[str, list[dict[str, Any]]] = {}
    for run in run_store.list_runs():
        task_id = str(run.get("task_id") or "").strip()
        run_id = str(run.get("run_id") or "").strip()
        if task_id and run_id:
            runs_by_task.setdefault(task_id, []).append(run)

    findings: list[dict[str, Any]] = []
    for task in tasks:
        task_id = str(task["task_id"])
        owner_role = str(task.get("owner_role") or "").strip()
        runs = runs_by_task.get(task_id) or []
        run_ids = [str(run.get("run_id") or "").strip() for run in runs if run.get("run_id")]
        latest_run_id = run_ids[-1] if run_ids else ""
        excerpt = (
            _specialist_reply_excerpt(workspace_id, latest_run_id) if latest_run_id else ""
        )
        findings.append(
            {
                "task_id": task_id,
                "plan_key": str(task.get("plan_key") or ""),
                "owner_role": owner_role,
                "assignee_name": _roster_name_for_role(workspace_id, owner_role)
                or str(task.get("assignee_name") or ""),
                "status": str(task.get("status") or ""),
                "outcome": str(task.get("terminal_outcome") or ""),
                "goal": str(task.get("goal") or ""),
                "acceptance_criteria": str(task.get("acceptance_criteria") or ""),
                "run_ids": run_ids,
                "specialist_reply_excerpt": excerpt,
                "attachment_ids": list(task.get("attachment_ids") or []),
                "output_artifacts": list(task.get("output_artifacts") or []),
            }
        )

    lines = []
    for row in findings:
        label = row["assignee_name"] or row["owner_role"] or "specialist"
        line = f"{label}={row['status']}"
        if row["outcome"]:
            line = f"{line} ({row['outcome']})"
        lines.append(line)
    summary = "; ".join(lines)
    return summary, findings


def _post_synthesis_handoffs(
    *,
    plan_id: str,
    workspace_id: str,
    goal: str,
    summary: str,
    findings: list[dict[str, Any]],
    synthesis_receipt_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from app.workspace_agents.lead_dana_report import post_lead_synthesis_to_dana_ide
    from app.workspace_agents.lead_vaxon_handoff import post_lead_synthesis_to_vaxon

    vaxon: dict[str, Any] = {}
    dana: dict[str, Any] = {}
    try:
        vaxon = post_lead_synthesis_to_vaxon(
            plan_id=plan_id,
            workspace_id=workspace_id,
            goal=goal,
            summary=summary,
            findings=findings,
            synthesis_receipt_id=synthesis_receipt_id,
        )
    except Exception:
        vaxon = {"status": "handoff_failed"}
    try:
        dana = post_lead_synthesis_to_dana_ide(
            plan_id=plan_id,
            workspace_id=workspace_id,
            goal=goal,
            summary=summary,
            findings=findings,
            synthesis_receipt_id=synthesis_receipt_id,
        )
    except Exception:
        dana = {"status": "handoff_failed"}
    return vaxon, dana


def synthesize_lead_plan(plan_id: str) -> dict[str, Any]:
    """Summarize terminal specialist task outcomes and persist a synthesis receipt."""
    plan = lead_plan_store.get_plan(plan_id)
    if plan is None:
        raise LeadReplanError(f"lead plan not found: {plan_id}")
    workspace_id = str(plan["workspace_id"])
    goal = str(plan.get("goal") or "")
    tasks = _plan_tasks(plan_id)
    pending = [
        str(task["task_id"])
        for task in tasks
        if str(task.get("status") or "").strip().lower() not in _TERMINAL_TASK_STATUSES
    ]
    if pending:
        return {
            "plan_id": plan_id,
            "status": "awaiting_results",
            "pending_task_ids": pending,
            "summary": "",
        }

    plan_status = str(plan.get("status") or "").strip().lower()
    if plan_status in {"completed", "awaiting_engagement"}:
        prior = next(
            (
                row
                for row in lead_plan_store.list_receipts(plan_id)
                if str(row.get("kind") or "") == "lead_synthesis_completed"
            ),
            None,
        )
        payload = (prior or {}).get("payload") if isinstance(prior, dict) else {}
        summary = str((payload or {}).get("summary") or "")
        findings = list((payload or {}).get("findings") or [])
        vaxon, dana = _post_synthesis_handoffs(
            plan_id=plan_id,
            workspace_id=workspace_id,
            goal=goal,
            summary=summary,
            findings=findings,
            synthesis_receipt_id=str((prior or {}).get("receipt_id") or ""),
        )
        return {
            "plan_id": plan_id,
            "status": plan_status if plan_status == "awaiting_engagement" else "completed",
            "summary": summary,
            "findings": findings,
            "receipt_id": (prior or {}).get("receipt_id"),
            "vaxon_handoff": vaxon,
            "dana_handoff": dana,
        }

    summary, findings = _build_synthesis_findings(workspace_id=workspace_id, tasks=tasks)
    lead_plan_store.set_plan_status(plan_id, "completed")
    receipt = lead_plan_store.append_receipt(
        plan_id=plan_id,
        workspace_id=workspace_id,
        kind="lead_synthesis_completed",
        payload={"summary": summary, "findings": findings},
    )
    vaxon, dana = _post_synthesis_handoffs(
        plan_id=plan_id,
        workspace_id=workspace_id,
        goal=goal,
        summary=summary,
        findings=findings,
        synthesis_receipt_id=str(receipt["receipt_id"]),
    )
    return {
        "plan_id": plan_id,
        "status": "completed",
        "summary": summary,
        "findings": findings,
        "receipt_id": receipt["receipt_id"],
        "vaxon_handoff": vaxon,
        "dana_handoff": dana,
    }


def maybe_synthesize_lead_plan_for_task(task_id: str) -> dict[str, Any] | None:
    """Idempotent synthesize when a lead-plan task becomes terminal."""
    plan_id = lead_plan_store.plan_id_for_task(task_id)
    if not plan_id:
        return None
    plan = lead_plan_store.get_plan(plan_id)
    if plan is None:
        return None
    status = str(plan.get("status") or "").strip().lower()
    if status not in _ACTIVE_SYNTH_PLAN_STATUSES:
        return None
    return synthesize_lead_plan(plan_id)


def notify_vaxon_after_lead_shift(
    *,
    workspace_id: str,
    run_id: str,
    employee_name: str,
    phase: str,
    reply_text: str | None = None,
) -> dict[str, Any]:
    """When Dana/Lead finishes their own shift, publish one VAXON operator flash.

    Specialists already reach VAXON via Lead takeover. Lead self-completions were
    previously silent — REPORT and the operator thread never saw the rollup.
    """
    cleaned_run = str(run_id or "").strip()
    workspace = str(workspace_id or "").strip()
    if not cleaned_run or not workspace:
        return {"status": "skipped_missing_ids"}

    from app.workspace_agents.lead_takeover import (
        _lead_summary_from_reply,
        extract_blockers,
        extract_lead_next,
    )
    from app.workspace_agents.lead_vaxon_handoff import post_ad_hoc_lead_takeover_to_vaxon

    name = (employee_name or "Lead").strip() or "Lead"
    terminal = phase if phase in {"completed", "failed"} else (phase or "ended")
    try:
        vaxon_flash = post_ad_hoc_lead_takeover_to_vaxon(
            workspace_id=workspace,
            run_id=cleaned_run,
            employee_role="lead",
            employee_name=name,
            phase=terminal,
            lead_next=extract_lead_next(reply_text),
            lead_summary=_lead_summary_from_reply(reply_text),
            blockers=extract_blockers(reply_text),
            reply_text=None,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "detail": str(exc), "run_id": cleaned_run}

    return {
        "status": "ok_lead_shift",
        "run_id": cleaned_run,
        "vaxon_flash": vaxon_flash,
    }


def notify_lead_after_worker_task(
    *,
    workspace_id: str,
    task_id: str,
    run_id: str,
    employee_role: str,
    employee_name: str,
    phase: str,
    reply_text: str | None = None,
) -> dict[str, Any]:
    """Specialist → Lead takeover (always), then plan status + auto-synthesize when terminal.

    Lead's own shifts post a VAXON flash (no Dana takeover of themselves).
    Works for continuous-worker tasks and ad-hoc IDE specialist shifts. Lead plans are
    optional — missing plan links no longer drop the Dana report.
    """
    role = str(employee_role or "").strip().lower()
    if role == "lead":
        return notify_vaxon_after_lead_shift(
            workspace_id=workspace_id,
            run_id=run_id,
            employee_name=employee_name,
            phase=phase if phase in {"completed", "failed"} else phase,
            reply_text=reply_text,
        )

    from app.workspace_agents.lead_checkin_assign import SPECIALIST_ROLES

    if role not in SPECIALIST_ROLES:
        return {"status": "skipped_not_specialist", "employee_role": role}

    task = task_store.get_task(task_id) if str(task_id or "").strip() else None
    task_status = str((task or {}).get("status") or "").strip().lower()
    if task is not None and task_status not in _TERMINAL_TASK_STATUSES:
        # fail_task may reopen when attempt budget remains.
        return {"status": "skipped_task_not_terminal", "task_status": task_status}

    plan_id = lead_plan_store.plan_id_for_task(task_id) if task else None
    goal = str((task or {}).get("goal") or "")
    outcome = str((task or {}).get("terminal_outcome") or "")

    from app.workspace_agents.lead_takeover import post_lead_takeover_report

    takeover = post_lead_takeover_report(
        workspace_id=workspace_id,
        run_id=run_id,
        employee_role=role,
        employee_name=employee_name,
        phase=phase if phase in {"completed", "failed"} else (task_status or phase),
        goal=goal,
        outcome=outcome,
        reply_text=reply_text,
        plan_id=plan_id,
        task_id=str(task_id or "").strip() or None,
        create_follow_up_task=True,
    )

    if not plan_id:
        return {
            "status": "ok_ad_hoc",
            "plan_id": None,
            "takeover": takeover,
            "specialist_status": {"status": "skipped_not_lead_plan"},
            "synthesis": None,
        }

    plan_key = None
    for link in lead_plan_store.plan_task_links(plan_id):
        if link.get("task_id") == task_id:
            plan_key = link.get("plan_key")
            break

    from app.workspace_agents.lead_dana_report import post_specialist_status_to_dana

    status_post = post_specialist_status_to_dana(
        workspace_id=workspace_id,
        plan_id=plan_id,
        task_id=task_id,
        plan_key=plan_key,
        run_id=run_id,
        employee_role=employee_role,
        employee_name=employee_name,
        phase=phase if phase in {"completed", "failed"} else task_status,
        goal=goal,
        outcome=outcome,
        reply_excerpt=(reply_text or "")[:400],
    )
    synthesis = maybe_synthesize_lead_plan_for_task(task_id)
    return {
        "status": "ok",
        "plan_id": plan_id,
        "takeover": takeover,
        "specialist_status": status_post,
        "synthesis": synthesis,
    }


def _cancel_obsolete_tasks(plan_id: str) -> tuple[list[str], list[dict[str, str]]]:
    cancelled: list[str] = []
    stop_errors: list[dict[str, str]] = []
    active_tasks = [
        task
        for task in _plan_tasks(plan_id)
        if str(task.get("status") or "").strip().lower()
        not in _TERMINAL_TASK_STATUSES
    ]
    # Stop every leased run first. Fail closed: never release path ownership and
    # start replacement work while an old process might still be running.
    for task in active_tasks:
        status = str(task.get("status") or "").strip().lower()
        run_id = str(task.get("run_id") or "").strip()
        if status == "leased" and run_id:
            try:
                stop_run(run_id)
            except (RunLifecycleError, RunNotFoundError, OSError, RuntimeError) as exc:
                stop_errors.append({"run_id": run_id, "detail": str(exc)})
    if stop_errors:
        return cancelled, stop_errors
    for task in active_tasks:
        task_store.cancel_task(
            str(task["task_id"]),
            terminal_outcome=f"superseded by Lead replan from {plan_id}",
        )
        cancelled.append(str(task["task_id"]))
    return cancelled, stop_errors


def replan_lead_goal(
    *,
    workspace_id: str,
    goal: str,
    mode: PlanMode = "auto",
    create_runs: bool = True,
) -> dict[str, Any]:
    """Supersede the active plan, cancel obsolete work, and materialize a new plan."""
    workspace = workspace_id.strip()
    cleaned_goal = " ".join((goal or "").strip().split())
    if not workspace:
        raise LeadReplanError("workspace_id is required")
    if not cleaned_goal:
        raise LeadReplanError("goal is required")

    previous = lead_plan_store.latest_active_plan(workspace)
    previous_plan_id = str(previous["plan_id"]) if previous else None
    cancelled: list[str] = []
    stop_errors: list[dict[str, str]] = []
    if previous_plan_id:
        cancelled, stop_errors = _cancel_obsolete_tasks(previous_plan_id)
        if stop_errors:
            lead_plan_store.append_receipt(
                plan_id=previous_plan_id,
                workspace_id=workspace,
                kind="lead_replan_blocked",
                payload={
                    "replacement_goal": cleaned_goal,
                    "stop_errors": stop_errors,
                },
            )
            raise LeadReplanError(
                "replan blocked because obsolete worker runs could not be stopped"
            )
        lead_plan_store.set_plan_status(previous_plan_id, "superseded")
        lead_plan_store.append_receipt(
            plan_id=previous_plan_id,
            workspace_id=workspace,
            kind="lead_plan_superseded",
            payload={
                "replacement_goal": cleaned_goal,
                "cancelled_task_ids": cancelled,
                "stop_errors": stop_errors,
            },
        )

    materialized = materialize_lead_fan_out(
        workspace_id=workspace,
        goal=cleaned_goal,
        mode=mode,
        create_runs=create_runs,
        supersedes_plan_id=previous_plan_id,
    )
    receipt = lead_plan_store.append_receipt(
        plan_id=str(materialized["plan_id"]),
        workspace_id=workspace,
        kind="lead_replan_materialized",
        payload={
            "supersedes_plan_id": previous_plan_id,
            "cancelled_task_ids": cancelled,
            "stop_errors": stop_errors,
        },
    )
    return {
        **materialized,
        "replan": {
            "supersedes_plan_id": previous_plan_id,
            "cancelled_task_ids": cancelled,
            "stop_errors": stop_errors,
            "receipt_id": receipt["receipt_id"],
        },
    }


__all__ = [
    "LeadReplanError",
    "maybe_synthesize_lead_plan_for_task",
    "notify_lead_after_worker_task",
    "notify_vaxon_after_lead_shift",
    "replan_lead_goal",
    "synthesize_lead_plan",
]
