"""Scheduler-driven Lead team check-in with role-assignment guardrails.

Runs on the continuous-worker clock (same tick path as file-size patrol).
Each enabled company Lead scans failed shifts + watch monitors/connectors,
then either assigns the matching specialist or escalates operator-only blockers
(usage limits / runtime auth) into the Lead IDE thread.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.persistence import chat_store, task_store
from app.workspace_agents.config_loader import load_workspace_agent_configs
from app.workspace_agents.lead_checkin_assign import (
    ASSIGN_GOAL_PREFIX,
    ATTEND_GOAL_PREFIX,
    CHECKIN_GOAL_PREFIX,
    SPECIALIST_ROLES,
    LeadCheckinFinding,
    assign_owner_role_for_failed_shift,
    assign_owner_role_for_monitor,
)
from app.workspace_agents.autonomous_attention_policy import attention_finding_auto_dispatches
from app.workspace_agents.run_outcome import latest_role_run_outcome

logger = logging.getLogger(__name__)

DEFAULT_MIN_INTERVAL_SECONDS = 900.0
DEFAULT_MAX_ASSIGNMENTS_PER_WORKSPACE = 2
SKIP_OUTCOME_ROLES = frozenset({"lead", "overview_agent"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc_now_iso() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _state_path() -> Path:
    raw = os.environ.get("AXON_WATCH_STATE_DIR", "./.local/state").strip() or "./.local/state"
    root = Path(raw).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    return root / "lead-team-checkin.json"


def _load_cooldown_state(path: Path | None = None) -> dict[str, Any]:
    target = path or _state_path()
    if not target.is_file():
        return {"workspaces": {}}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"workspaces": {}}
    if not isinstance(payload, dict):
        return {"workspaces": {}}
    if not isinstance(payload.get("workspaces"), dict):
        payload["workspaces"] = {}
    return payload


def _save_cooldown_state(state: dict[str, Any], path: Path | None = None) -> None:
    target = path or _state_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        logger.exception("could not persist lead check-in cooldown state")


def _parse_iso(raw: str | None) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def workspace_due_for_checkin(
    workspace_id: str,
    *,
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    now: datetime | None = None,
    state_path: Path | None = None,
) -> bool:
    state = _load_cooldown_state(state_path)
    workspaces = state.get("workspaces") if isinstance(state.get("workspaces"), dict) else {}
    stamp = _parse_iso(str((workspaces.get(workspace_id) or {}).get("last_checkin_at") or ""))
    if stamp is None:
        return True
    current = now or _utc_now()
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    elapsed = (current - stamp.astimezone(timezone.utc)).total_seconds()
    return elapsed >= max(60.0, float(min_interval_seconds))


def mark_workspace_checked_in(
    workspace_id: str,
    *,
    now: datetime | None = None,
    state_path: Path | None = None,
) -> None:
    state = _load_cooldown_state(state_path)
    workspaces = state.setdefault("workspaces", {})
    if not isinstance(workspaces, dict):
        workspaces = {}
        state["workspaces"] = workspaces
    workspaces[workspace_id] = {
        "last_checkin_at": (now or _utc_now()).isoformat().replace("+00:00", "Z")
    }
    _save_cooldown_state(state, state_path)


def _employee_id_for_role(workspace_id: str, role: str) -> str | None:
    from app.workspace_agents import build_company_roster

    company = build_company_roster(workspace_id)
    rows = company.get("employees") if isinstance(company, dict) else None
    if not isinstance(rows, list):
        return None
    want = role.strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        if str(row.get("role") or "").strip().lower() == want:
            employee_id = str(row.get("employee_id") or "").strip()
            return employee_id or None
    return None


def _post_lead_checkin_message(
    *,
    workspace_id: str,
    findings: list[LeadCheckinFinding],
    assigned: list[dict[str, Any]],
) -> str | None:
    employee_id = _employee_id_for_role(workspace_id, "lead")
    if not employee_id:
        return None
    created_at = _utc_now_iso()
    thread = chat_store.find_thread_for_employee(
        workspace_id,
        employee_id=employee_id,
        thread_kind="ide",
    )
    if thread is None:
        thread = chat_store.create_thread(
            workspace_id=workspace_id,
            run_id=None,
            created_at=created_at,
            thread_kind="ide",
            title="Lead · team check-in",
            employee_id=employee_id,
            employee_role="lead",
        )
    thread_id = str(thread["thread_id"])
    lines = [
        f"{CHECKIN_GOAL_PREFIX} scheduled team health pass.",
        f"Findings: {len(findings)} · Assignments created: {len(assigned)}",
        "",
    ]
    for index, finding in enumerate(findings[:12], start=1):
        flag = "ESCALATE" if finding.escalate_only else f"→ {finding.owner_role}"
        lines.append(f"{index}. [{finding.kind}] {finding.title} ({flag})")
        # finding.detail already went through normalize_operator_failure_detail +
        # word-boundary truncation upstream (run_outcome.latest_role_run_outcome) —
        # do not re-normalize or re-truncate it here.
        if finding.detail:
            lines.append(f"   {finding.detail}")
    if not findings:
        lines.append("No failed shifts or degraded third-party signals this pass.")
    # No trailing "Hierarchy" / "Confidence" boilerplate: this is a deterministic
    # status message, not an LLM turn — there's no model self-assessment to score,
    # and the org-chart line is unparsed narration repeated on every check-in with
    # no reader value (see app.kairo_conversation_runtime_context for the actual
    # functional hierarchy line, which feeds VAXON's own reasoning context instead).
    message_id = f"message_system_{uuid4().hex}"
    chat_store.save_message(
        {
            "message_id": message_id,
            "thread_id": thread_id,
            "workspace_id": workspace_id,
            "run_id": None,
            "role": "agent",
            "content": "\n".join(lines),
            "created_at": created_at,
        }
    )
    return message_id


def collect_failed_shift_findings(workspace_id: str) -> list[LeadCheckinFinding]:
    findings: list[LeadCheckinFinding] = []
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    company = companies.get(workspace_id)
    if company is None:
        return findings
    for employee in company.employees:
        role = str(employee.role or "").strip().lower()
        if not role or role in SKIP_OUTCOME_ROLES:
            continue
        outcome = latest_role_run_outcome(workspace_id, role)
        if not outcome or str(outcome.get("outcome") or "").strip().lower() != "failed":
            continue
        # latest_role_run_outcome already ran normalize_operator_failure_detail +
        # truncation — re-normalizing here was redundant work on already-clean text.
        detail = str(outcome.get("detail") or "")
        owner_role, escalate_only = assign_owner_role_for_failed_shift(role, detail)
        run_id = str(outcome.get("run_id") or "").strip() or "unknown"
        name = str(employee.name or role).strip() or role
        findings.append(
            LeadCheckinFinding(
                kind="operator_blocker" if escalate_only else "failed_shift",
                workspace_id=workspace_id,
                owner_role=owner_role,
                title=f"{name} ({role}) last shift failed",
                detail=detail or "failed shift without detail",
                dedupe_key=f"failed_shift:{workspace_id}:{role}:{run_id}",
                escalate_only=escalate_only,
            )
        )
    return findings


def collect_watch_findings(
    workspace_id: str,
    *,
    monitors_payload: dict[str, Any] | None = None,
    connectors_payload: dict[str, Any] | None = None,
) -> list[LeadCheckinFinding]:
    findings: list[LeadCheckinFinding] = []

    monitors = monitors_payload
    if monitors is None:
        try:
            from app.adapters.watch_client import fetch_watch_monitors

            monitors = fetch_watch_monitors(timeout_seconds=2.0)
        except Exception:  # noqa: BLE001 — check-in must stay fail-open
            monitors = None
    records: list[Any] = []
    if isinstance(monitors, dict):
        raw = monitors.get("records") or monitors.get("monitors") or []
        if isinstance(raw, list):
            records = raw
    for record in records:
        if not isinstance(record, dict):
            continue
        record_workspace = str(record.get("workspace_id") or "").strip()
        if record_workspace and record_workspace != workspace_id:
            continue
        status = str(record.get("status") or "").strip().lower()
        if status in {"", "ok", "skipped"}:
            continue
        check_id = str(record.get("check_id") or "").strip() or "monitor"
        check_type = str(record.get("check_type") or "").strip()
        service = str(record.get("service") or check_type).strip()
        detail = str(record.get("detail") or "").strip()
        owner = assign_owner_role_for_monitor(check_type, service)
        findings.append(
            LeadCheckinFinding(
                kind="monitor_alert",
                workspace_id=workspace_id,
                owner_role=owner,
                title=f"{service} monitor {status}",
                detail=detail or f"{check_id} reported {status}",
                dedupe_key=f"monitor:{workspace_id}:{check_id}:{status}",
            )
        )

    connectors = connectors_payload
    if connectors is None:
        try:
            from app.adapters.watch_client import fetch_watch_connectors

            connectors = fetch_watch_connectors(timeout_seconds=2.0)
        except Exception:  # noqa: BLE001
            connectors = None
    connector_rows: list[Any] = []
    if isinstance(connectors, dict):
        raw = connectors.get("connectors") or connectors.get("records") or []
        if isinstance(raw, list):
            connector_rows = raw
        elif isinstance(raw, dict):
            connector_rows = [
                {"connector_id": key, **value} if isinstance(value, dict) else {"connector_id": key}
                for key, value in raw.items()
            ]
    for record in connector_rows:
        if not isinstance(record, dict):
            continue
        record_workspace = str(record.get("workspace_id") or "").strip()
        if record_workspace and record_workspace != workspace_id:
            continue
        status = str(record.get("status") or "").strip().lower()
        if status not in {"degraded", "unavailable"}:
            continue
        required = bool(record.get("required", False))
        if not required and status == "unavailable":
            continue
        connector_id = str(record.get("connector_id") or record.get("id") or "connector").strip()
        name = str(record.get("display_name") or connector_id).strip()
        detail = str(record.get("detail") or "").strip()
        findings.append(
            LeadCheckinFinding(
                kind="connector_degraded",
                workspace_id=workspace_id,
                owner_role="integrations",
                title=f"{name} connector {status}",
                detail=detail or f"{connector_id} is {status}",
                dedupe_key=f"connector:{workspace_id}:{connector_id}:{status}",
            )
        )
    return findings


def collect_workspace_findings(
    workspace_id: str,
    *,
    monitors_payload: dict[str, Any] | None = None,
    connectors_payload: dict[str, Any] | None = None,
) -> list[LeadCheckinFinding]:
    return collect_failed_shift_findings(workspace_id) + collect_watch_findings(
        workspace_id,
        monitors_payload=monitors_payload,
        connectors_payload=connectors_payload,
    )


def _open_assignment_tasks(workspace_id: str) -> list[dict[str, Any]]:
    openish: list[dict[str, Any]] = []
    for status in ("open", "leased"):
        openish.extend(
            task_store.list_tasks(workspace_id=workspace_id, status=status, limit=200)
        )
    return [
        row
        for row in openish
        if str(row.get("goal") or "").startswith((ASSIGN_GOAL_PREFIX, ATTEND_GOAL_PREFIX))
    ]


def _already_tracked(dedupe_key: str, existing: list[dict[str, Any]]) -> bool:
    needle = dedupe_key.lower()
    for row in existing:
        goal = str(row.get("goal") or "").lower()
        criteria = str(row.get("acceptance_criteria") or "").lower()
        if needle in goal or needle in criteria:
            return True
    return False


def enqueue_lead_assignments(
    *,
    workspace_id: str,
    findings: list[LeadCheckinFinding],
    max_new_tasks: int = DEFAULT_MAX_ASSIGNMENTS_PER_WORKSPACE,
) -> list[dict[str, Any]]:
    """Create specialist tasks for assignable findings (not escalate-only)."""
    workspace = workspace_id.strip()
    if not workspace or int(max_new_tasks) <= 0:
        return []
    existing = _open_assignment_tasks(workspace)
    created: list[dict[str, Any]] = []
    assignable = [item for item in findings if attention_finding_auto_dispatches(item)]
    priority = {
        "failed_shift": 0,
        "monitor_alert": 1,
        "connector_degraded": 2,
        "operator_blocker": 9,
    }
    ordered = sorted(assignable, key=lambda item: (priority.get(item.kind, 5), item.dedupe_key))
    for finding in ordered:
        if len(created) >= max(1, int(max_new_tasks)):
            break
        if _already_tracked(finding.dedupe_key, existing + created):
            continue
        if finding.owner_role not in SPECIALIST_ROLES:
            continue
        try:
            record = task_store.create_task(
                workspace_id=workspace,
                goal=(
                    f"{ASSIGN_GOAL_PREFIX} {finding.title}. "
                    f"Investigate and fix; report receipts to Lead. "
                    f"[{finding.dedupe_key}]"
                ),
                acceptance_criteria=(
                    f"Resolve: {finding.detail}. "
                    "Post a short Lead-ready report with verified evidence only. "
                    "Never invent status. End with Confidence: N/10. "
                    f"dedupe={finding.dedupe_key}"
                ),
                # auto_safe only — escalate_only findings never reach create_task
                risk="normal",
                owner_role=finding.owner_role,
                attempt_budget=2,
            )
        except task_store.TaskLedgerError as exc:
            logger.warning("lead check-in could not create task: %s", exc)
            continue
        created.append(record)
    return created


def run_lead_team_checkin(
    *,
    min_interval_seconds: float = DEFAULT_MIN_INTERVAL_SECONDS,
    max_assignments_per_workspace: int = DEFAULT_MAX_ASSIGNMENTS_PER_WORKSPACE,
    workspace_ids: list[str] | None = None,
    state_path: Path | None = None,
    monitors_payload: dict[str, Any] | None = None,
    connectors_payload: dict[str, Any] | None = None,
    post_lead_message: bool = True,
) -> dict[str, Any]:
    """Tick Lead check-in across companies that are due on the clock."""
    _configs, _defaults, companies, _staffing = load_workspace_agent_configs()
    targets = workspace_ids or sorted(companies.keys())
    result: dict[str, Any] = {
        "work_source": "lead_team_checkin",
        "checked_workspaces": [],
        "skipped_cooldown": [],
        "findings": [],
        "created_tasks": [],
        "lead_messages": [],
    }
    for workspace_id in targets:
        workspace = str(workspace_id or "").strip()
        if not workspace or workspace not in companies:
            continue
        if not workspace_due_for_checkin(
            workspace,
            min_interval_seconds=min_interval_seconds,
            state_path=state_path,
        ):
            result["skipped_cooldown"].append(workspace)
            continue
        findings = collect_workspace_findings(
            workspace,
            monitors_payload=monitors_payload,
            connectors_payload=connectors_payload,
        )
        from app.workspace_agents.task_duplicate_cleanup import safe_reconcile_workspace_waiting_duplicates
        safe_reconcile_workspace_waiting_duplicates(workspace, log=logger)
        assigned = enqueue_lead_assignments(
            workspace_id=workspace,
            findings=findings,
            max_new_tasks=max_assignments_per_workspace,
        )
        message_id = None
        if post_lead_message and (findings or assigned):
            try:
                message_id = _post_lead_checkin_message(
                    workspace_id=workspace,
                    findings=findings,
                    assigned=assigned,
                )
            except Exception:  # noqa: BLE001
                logger.exception("lead check-in message failed for %s", workspace)
        mark_workspace_checked_in(workspace, state_path=state_path)
        result["checked_workspaces"].append(workspace)
        result["findings"].extend(item.to_dict() for item in findings)
        result["created_tasks"].extend(assigned)
        if message_id:
            result["lead_messages"].append(
                {"workspace_id": workspace, "message_id": message_id}
            )
    return result


__all__ = [
    "ASSIGN_GOAL_PREFIX",
    "CHECKIN_GOAL_PREFIX",
    "DEFAULT_MAX_ASSIGNMENTS_PER_WORKSPACE",
    "DEFAULT_MIN_INTERVAL_SECONDS",
    "LeadCheckinFinding",
    "assign_owner_role_for_failed_shift",
    "assign_owner_role_for_monitor",
    "collect_failed_shift_findings",
    "collect_watch_findings",
    "collect_workspace_findings",
    "enqueue_lead_assignments",
    "mark_workspace_checked_in",
    "run_lead_team_checkin",
    "workspace_due_for_checkin",
]
