"""Operator-facing CI signals and repair outcome reports."""

from __future__ import annotations

from typing import Any

from app.ci_remediation import store as ci_store
from app.adapters.watch_client import reset_watch_inbox_cache


def reset_ci_signal_store_for_tests() -> None:
    ci_store.reset_store_for_tests()


def failure_signal_id(dedupe_key: str) -> str:
    digest = dedupe_key.replace(":", "_").replace("/", "_")
    return f"signal_ci_fast_gate_{digest[-48:]}"


def emit_failure_signal(
    *,
    dedupe_key: str,
    workspace_id: str,
    workflow_name: str,
    head_branch: str,
    html_url: str,
    failing_step: str,
    run_id: str,
    display_title: str = "",
) -> dict[str, Any]:
    branch = head_branch or "unknown-branch"
    title = f"{workflow_name} failed on {branch}"
    summary_bits = [
        f"Run {run_id} concluded failure.",
        f"First hard-fail hint: {failing_step}.",
    ]
    if display_title:
        summary_bits.insert(0, display_title)
    if html_url:
        summary_bits.append(html_url)
    summary = " ".join(summary_bits)
    record = ci_store.upsert_signal(
        signal_id=failure_signal_id(dedupe_key),
        dedupe_key=dedupe_key,
        workspace_id=workspace_id,
        title=title,
        summary=summary,
        severity="high",
        status="open",
        html_url=html_url,
        meta={
            "signal_family": "ci_remediation",
            "workflow_name": workflow_name,
            "head_branch": head_branch,
            "run_id": run_id,
            "failing_step": failing_step,
            "phase": "failed",
        },
    )
    reset_watch_inbox_cache()
    return record


def mark_repair_outcome(
    *,
    dedupe_key: str,
    workspace_id: str,
    workflow_name: str,
    head_branch: str,
    success: bool,
    detail: str,
    html_url: str = "",
    draft_pr_url: str = "",
) -> dict[str, Any]:
    branch = head_branch or "unknown-branch"
    if success:
        title = f"{workflow_name} repaired on {branch}"
        summary = detail or "CI repair completed; draft PR ready for review."
        if draft_pr_url:
            summary = f"{summary} {draft_pr_url}"
        severity = "info"
        status = "resolved"
        phase = "repaired"
    else:
        title = f"{workflow_name} still red on {branch}"
        summary = detail or "CI repair attempt budget exhausted."
        severity = "critical"
        status = "open"
        phase = "blocked"
    record = ci_store.upsert_signal(
        signal_id=failure_signal_id(dedupe_key),
        dedupe_key=dedupe_key,
        workspace_id=workspace_id,
        title=title,
        summary=summary,
        severity=severity,
        status=status if success else "open",
        html_url=html_url or draft_pr_url,
        meta={
            "signal_family": "ci_remediation",
            "workflow_name": workflow_name,
            "head_branch": head_branch,
            "phase": phase,
            "draft_pr_url": draft_pr_url,
        },
    )
    ci_store.set_event_status(dedupe_key, "repaired" if success else "blocked")
    if success:
        try:
            from app.ci_remediation.dispatch_repair import supersede_prior_repair_tasks
            from app.persistence import task_store

            event = ci_store.get_event(dedupe_key)
            keep_task_id = str((event or {}).get("task_id") or "").strip() or None
            cancelled = supersede_prior_repair_tasks(
                workspace_id=workspace_id,
                classified={
                    "workflow_name": workflow_name,
                    "head_branch": head_branch,
                },
                keep_task_id=keep_task_id,
            )
            if keep_task_id:
                try:
                    task_store.complete_task(
                        keep_task_id,
                        terminal_outcome="ci repair reported success",
                    )
                except task_store.TaskLedgerError:
                    pass
            if cancelled:
                summary = f"{summary} Superseded {len(cancelled)} older repair task(s)."
                record = ci_store.upsert_signal(
                    signal_id=failure_signal_id(dedupe_key),
                    dedupe_key=dedupe_key,
                    workspace_id=workspace_id,
                    title=title,
                    summary=summary,
                    severity=severity,
                    status="resolved",
                    html_url=html_url or draft_pr_url,
                    meta={
                        "signal_family": "ci_remediation",
                        "workflow_name": workflow_name,
                        "head_branch": head_branch,
                        "phase": phase,
                        "draft_pr_url": draft_pr_url,
                        "superseded_task_count": len(cancelled),
                    },
                )
        except Exception:  # noqa: BLE001 — outcome report must still return
            pass
    reset_watch_inbox_cache()
    return record


def spoken_report_line(*, success: bool, workflow_name: str, detail: str) -> str:
    if success:
        return (
            f"{workflow_name} is green again after autonomous repair. "
            f"{detail}".strip()
        )
    return (
        f"{workflow_name} is still red after repair attempts. "
        f"{detail} Shall I triage the repair?".strip()
    )


def ci_inbox_items() -> list[dict[str, object]]:
    """Project open/repairing CI signals into watch-inbox shape for CP merge."""
    items: list[dict[str, object]] = []
    for row in ci_store.list_open_signals():
        meta = row.get("meta") if isinstance(row.get("meta"), dict) else {}
        items.append(
            {
                "signal_id": str(row.get("signal_id") or ""),
                "workspace_id": str(row.get("workspace_id") or "workspace_axon_watch"),
                "title": str(row.get("title") or "CI failure"),
                "summary": str(row.get("summary") or ""),
                "severity": str(row.get("severity") or "high"),
                "status": "open",
                "source": "ci_remediation",
                "created_at": str(row.get("created_at") or ""),
                "updated_at": str(row.get("updated_at") or ""),
                "action_type": "investigate",
                "delivery_state": "pending",
                "meta": meta,
                "watch_rule": {
                    "mode": "interrupt",
                    "reason": "ci_remediation_failure",
                    "interrupts": True,
                },
            }
        )
    return items
