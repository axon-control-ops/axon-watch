"""Operator-facing VAXON fleet-repair signals and outcome reports."""

from __future__ import annotations

import logging
import re
from typing import Any

from app.adapters.watch_client import reset_watch_inbox_cache
from app.fleet_self_heal import store
from app.fleet_self_heal.config import FleetSelfHealConfig, load_fleet_self_heal_config

logger = logging.getLogger(__name__)

# Mirrors critical_review_clause.py's Confidence: N/10 trailing-line pattern —
# same UX (agent ends its final reply with a structured line), reused here so
# reconciliation can recover a commit ref when the report-outcome webhook
# callback never arrives.
_FIX_COMMIT_RE = re.compile(r"Fix commit:\s*(\S.*)$", re.IGNORECASE | re.MULTILINE)


def reset_fleet_repair_store_for_tests() -> None:
    store.reset_store_for_tests()


def failure_signal_id(fingerprint: str) -> str:
    digest = fingerprint.replace(":", "_").replace("/", "_")
    return f"signal_fleet_repair_{digest[-48:]}"


def emit_failure_signal(
    *,
    fingerprint: str,
    workspace_id: str,
    subsystem: str,
    occurrence_count: int,
    file_hint: str = "",
    severity: str = "high",
) -> dict[str, Any]:
    title = f"VAXON fleet bug: {subsystem}"
    summary_bits = [f"{occurrence_count} occurrence(s) of fingerprint {fingerprint}."]
    if file_hint:
        summary_bits.append(f"Likely source: {file_hint}.")
    record = store.upsert_signal(
        signal_id=failure_signal_id(fingerprint),
        fingerprint=fingerprint,
        workspace_id=workspace_id,
        title=title,
        summary=" ".join(summary_bits),
        severity=severity,
        status="open",
        meta={
            "signal_family": "fleet_self_heal",
            "subsystem": subsystem,
            "file_hint": file_hint,
            "phase": "dispatched",
        },
    )
    reset_watch_inbox_cache()
    return record


def _escalate_to_lead(*, fingerprint: str, event: dict[str, Any], config: FleetSelfHealConfig) -> None:
    from app.persistence import task_store

    task_store.create_task(
        workspace_id=config.target_workspace_id,
        goal=(
            f"Lead: VAXON could not auto-repair fleet bug {fingerprint} after "
            f"{config.max_dispatch_cycles} dispatch cycles — decide: reassign to a "
            "specialist, escalate to operator, or accept as known-issue."
        ),
        acceptance_criteria=(
            f"Sole truth: unblock {fingerprint}. Review the failed attempts under "
            "this fingerprint's task history before deciding. End with Confidence: N/10."
        ),
        risk="normal",
        owner_role=config.escalate_role,
        attempt_budget=1,
    )


def mark_repair_outcome(
    *,
    fingerprint: str,
    success: bool,
    commit_ref: str = "",
    detail: str = "",
    config: FleetSelfHealConfig | None = None,
) -> dict[str, Any]:
    cfg = config or load_fleet_self_heal_config()
    event = store.get_event(fingerprint)
    observed_workspaces = (event or {}).get("workspaces_json") or ["workspace_axon_watch"]
    workspace_id = observed_workspaces[0] if observed_workspaces else "workspace_axon_watch"
    subsystem = str((event or {}).get("subsystem") or "unknown")

    if success:
        store.record_verified_fix(fingerprint, commit_ref=commit_ref or "unknown")
        title = f"VAXON fleet bug repaired: {subsystem}"
        summary = detail or "Fleet-infra repair verified via Gate 6 + Critical Review."
        if commit_ref:
            summary = f"{summary} Commit: {commit_ref}."
        signal = store.upsert_signal(
            signal_id=failure_signal_id(fingerprint),
            fingerprint=fingerprint,
            workspace_id=workspace_id,
            title=title,
            summary=summary,
            severity="info",
            status="resolved",
            meta={"signal_family": "fleet_self_heal", "subsystem": subsystem, "phase": "verified_fixed"},
        )
        task_id = str((event or {}).get("task_id") or "").strip()
        if task_id:
            try:
                from app.persistence import task_store

                task_store.complete_task(task_id, terminal_outcome="VAXON fleet repair verified fixed")
            except Exception:  # noqa: BLE001 — signal state is primary, task cleanup is best-effort
                logger.exception("could not complete VAXON fleet repair task %s", task_id)
        reset_watch_inbox_cache()
        return signal

    attempts_used = store.bump_attempts(fingerprint)
    if attempts_used >= cfg.max_dispatch_cycles:
        store.set_event_status(fingerprint, "blocked")
        if event is not None:
            try:
                _escalate_to_lead(fingerprint=fingerprint, event=event, config=cfg)
            except Exception:  # noqa: BLE001 — escalation must not crash the callback
                logger.exception("VAXON fleet repair Lead escalation failed for %s", fingerprint)
        title = f"VAXON fleet bug blocked: {subsystem}"
        summary = detail or f"Auto-repair exhausted after {attempts_used} dispatch cycle(s); escalated to Lead."
        severity = "critical"
    else:
        title = f"VAXON fleet bug still open: {subsystem}"
        summary = detail or f"Repair attempt {attempts_used}/{cfg.max_dispatch_cycles} failed; will retry."
        severity = "high"

    signal = store.upsert_signal(
        signal_id=failure_signal_id(fingerprint),
        fingerprint=fingerprint,
        workspace_id=workspace_id,
        title=title,
        summary=summary,
        severity=severity,
        status="open",
        meta={"signal_family": "fleet_self_heal", "subsystem": subsystem, "phase": "repairing"},
    )
    reset_watch_inbox_cache()
    return signal


def _parse_fix_commit_from_run(history_ref: str) -> str:
    from app.persistence import run_store

    for item in reversed(run_store.list_history(history_ref)):
        receipt = item.get("receipt") if isinstance(item, dict) else None
        if not isinstance(receipt, dict):
            continue
        summary = str(receipt.get("summary") or "")
        match = _FIX_COMMIT_RE.search(summary)
        if match:
            return match.group(1).strip()
    return ""


def reconcile_linked_fleet_repair_outcomes(*, config: FleetSelfHealConfig | None = None) -> list[dict[str, str]]:
    """Retire fleet-repair alerts whose linked task already finished.

    report-outcome is the fast path, but the callback can be missed. Completed
    tasks are durable proof the repair worker's own reply passed Gate 6 +
    Critical Review; recover a commit_ref from a trailing "Fix commit: ..."
    line in its final reply if the callback never arrived.
    """
    try:
        from app.persistence import task_store
    except Exception:  # noqa: BLE001 — a read-side recovery must fail open
        return []

    cfg = config or load_fleet_self_heal_config()
    reconciled: list[dict[str, str]] = []
    for signal in store.list_open_signals():
        fingerprint = str(signal.get("fingerprint") or "").strip()
        event = store.get_event(fingerprint)
        if event is None or event.get("status") not in {"dispatched", "repairing"}:
            continue
        task_id = str(event.get("task_id") or "").strip()
        if not task_id:
            continue
        task = task_store.get_task(task_id)
        task_status = str((task or {}).get("status") or "").strip().lower()
        if task_status != "completed":
            continue
        run_id = str((task or {}).get("run_id") or "").strip()
        commit_ref = ""
        if run_id:
            from app.persistence import run_store

            run = run_store.get_run(run_id)
            if run is not None:
                commit_ref = _parse_fix_commit_from_run(str(run.get("history_ref") or ""))
        mark_repair_outcome(
            fingerprint=fingerprint,
            success=True,
            commit_ref=commit_ref or "unknown (recovered via task completion — confirm manually)",
            detail="Recovered via task completion; report-outcome callback was not received.",
            config=cfg,
        )
        reconciled.append({"fingerprint": fingerprint, "task_id": task_id, "reason": "linked_repair_task_completed"})
    return reconciled


def spoken_report_line(*, success: bool, subsystem: str, detail: str) -> str:
    if success:
        return f"{subsystem} fleet bug is fixed and verified. {detail}".strip()
    return f"{subsystem} fleet bug repair attempt failed. {detail}".strip()


def fleet_repair_inbox_items(*, config: FleetSelfHealConfig | None = None) -> list[dict[str, object]]:
    """Project open/repairing fleet-repair signals into watch-inbox shape."""
    reconcile_linked_fleet_repair_outcomes(config=config)
    items: list[dict[str, object]] = []
    for row in store.list_open_signals():
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        severity = str(row.get("severity") or "high")
        items.append(
            {
                "signal_id": str(row.get("signal_id") or ""),
                "workspace_id": str(row.get("workspace_id") or "workspace_axon_watch"),
                "title": str(row.get("title") or "Fleet bug"),
                "summary": str(row.get("summary") or ""),
                "severity": severity,
                "status": "open",
                "source": "fleet_self_heal",
                "created_at": str(row.get("created_at") or ""),
                "updated_at": str(row.get("updated_at") or ""),
                "action_type": "investigate",
                "delivery_state": "pending",
                "meta": meta,
                "watch_rule": {
                    "mode": "interrupt" if severity in {"high", "critical"} else "observe",
                    "reason": "fleet_self_heal_failure",
                    "interrupts": severity in {"high", "critical"},
                },
            }
        )
    return items


__all__ = [
    "emit_failure_signal",
    "failure_signal_id",
    "fleet_repair_inbox_items",
    "mark_repair_outcome",
    "reconcile_linked_fleet_repair_outcomes",
    "reset_fleet_repair_store_for_tests",
    "spoken_report_line",
]
