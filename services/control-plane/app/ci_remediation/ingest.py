"""Orchestrate Gate 9 workflow_run failure → signal → lease → dispatch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.ci_remediation.classify import classify_workflow_run_event, dedupe_key
from app.ci_remediation.config import match_binding
from app.ci_remediation.dispatch_repair import (
    create_and_lease_repair_task,
    dispatch_repair_run,
)
from app.ci_remediation import store as ci_store
from app.ci_remediation.report import emit_failure_signal
from app.persistence import task_store
from app.workspace_delivery.ci_status import (
    apply_ci_status_to_delivery,
    classify_workflow_status,
)


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    reason: str
    dedupe_key: str = ""
    task_id: str = ""
    run_id: str = ""
    signal_id: str = ""
    duplicate: bool = False
    delivery_id: str = ""


def _track_delivery_status(payload: dict[str, Any]) -> dict[str, Any] | None:
    status = classify_workflow_status(payload)
    if status is None:
        return None
    binding = match_binding(
        github_owner=status["github_owner"],
        github_repo=status["github_repo"],
        workflow_name=status["workflow_name"],
        enabled_only=True,
    )
    if binding is None:
        return None
    return apply_ci_status_to_delivery(
        workspace_id=binding.workspace_id,
        head_branch=status.get("head_branch") or "",
        head_sha=status.get("head_sha") or "",
        kind=status["kind"],
        html_url=status.get("html_url") or "",
        conclusion=status.get("conclusion") or "",
        workflow_name=status.get("workflow_name") or "",
    )


def _clear_stale_on_success(payload: dict[str, Any]) -> int:
    """Resolve older open CI failure alerts when this event is a green run."""
    status = classify_workflow_status(payload)
    if status is None or str(status.get("kind") or "") != "success":
        return 0
    from app.ci_remediation.stale_sweep import resolve_open_for_branch_success

    cleared = resolve_open_for_branch_success(
        workflow_name=str(status.get("workflow_name") or ""),
        head_branch=str(status.get("head_branch") or ""),
        head_sha=str(status.get("head_sha") or ""),
    )
    return len(cleared)


def ingest_workflow_run_event(
    payload: dict[str, Any],
    *,
    dispatch: bool | None = None,
) -> IngestResult:
    delivery = _track_delivery_status(payload)
    delivery_id = str((delivery or {}).get("delivery_id") or "")

    stale_cleared = 0
    try:
        stale_cleared = _clear_stale_on_success(payload)
    except Exception:  # noqa: BLE001 — never block ingest on stale clear
        import logging

        logging.getLogger(__name__).exception("ci success stale-clear failed")

    classified = classify_workflow_run_event(payload)
    if classified is None:
        if delivery is not None:
            reason = f"delivery_status:{delivery.get('stage')}"
            if stale_cleared:
                reason = f"{reason};stale_cleared:{stale_cleared}"
            return IngestResult(
                accepted=True,
                reason=reason,
                delivery_id=delivery_id,
                run_id=str(delivery.get("run_id") or ""),
            )
        if stale_cleared:
            return IngestResult(
                accepted=True,
                reason=f"stale_cleared:{stale_cleared}",
                delivery_id=delivery_id,
            )
        return IngestResult(accepted=False, reason="not_a_completed_failure")

    # Escalated deliveries must not spawn more repair attempts.
    if delivery is not None and str(delivery.get("stage") or "") == "escalated":
        return IngestResult(
            accepted=True,
            reason="delivery_escalated",
            delivery_id=delivery_id,
            run_id=str(delivery.get("run_id") or ""),
        )

    binding = match_binding(
        github_owner=classified["github_owner"],
        github_repo=classified["github_repo"],
        workflow_name=classified["workflow_name"],
        enabled_only=True,
    )
    if binding is None:
        return IngestResult(
            accepted=False,
            reason="no_enabled_binding",
            delivery_id=delivery_id,
        )

    key = dedupe_key(
        github_owner=classified["github_owner"],
        github_repo=classified["github_repo"],
        workflow_name=classified["workflow_name"],
        head_branch=classified.get("head_branch") or "",
        head_sha=classified.get("head_sha") or "",
    )
    existing = ci_store.get_event(key)
    if existing is not None and str(existing.get("status") or "") in {
        "open",
        "repairing",
    }:
        return IngestResult(
            accepted=True,
            reason="duplicate_open_event",
            dedupe_key=key,
            task_id=str(existing.get("task_id") or ""),
            run_id=str(existing.get("run_id") or ""),
            duplicate=True,
            delivery_id=delivery_id,
        )

    ci_store.upsert_open_event(
        dedupe_key=key,
        run_id=classified["run_id"],
        workspace_id=binding.workspace_id,
        payload=classified,
    )
    signal = emit_failure_signal(
        dedupe_key=key,
        workspace_id=binding.workspace_id,
        workflow_name=classified["workflow_name"],
        head_branch=classified.get("head_branch") or "",
        html_url=classified.get("html_url") or "",
        failing_step=classified.get("failing_step") or "unknown failing step",
        run_id=classified["run_id"],
        display_title=classified.get("display_title") or "",
    )

    if delivery is not None and str(delivery.get("stage") or "") == "ci_red":
        from app.workspace_delivery import store as delivery_store

        delivery_store.update_delivery(
            str(delivery["delivery_id"]),
            stage="repairing",
        )

    try:
        leased = create_and_lease_repair_task(
            binding=binding,
            classified=classified,
            dedupe_key=key,
        )
    except task_store.TaskLedgerError as exc:
        return IngestResult(
            accepted=False,
            reason=f"task_create_failed:{exc}",
            dedupe_key=key,
            signal_id=str(signal.get("signal_id") or ""),
            delivery_id=delivery_id,
        )

    task_id = str(leased.get("task_id") or "")
    ci_store.attach_task(key, task_id, status="repairing")

    should_dispatch = binding.dispatch_on_ingest if dispatch is None else dispatch
    run_record = None
    if should_dispatch:
        run_record = dispatch_repair_run(
            binding=binding,
            leased_task=leased,
            classified=classified,
        )

    return IngestResult(
        accepted=True,
        reason="ingested",
        dedupe_key=key,
        task_id=task_id,
        run_id=str((run_record or {}).get("run_id") or classified["run_id"]),
        signal_id=str(signal.get("signal_id") or ""),
        duplicate=False,
        delivery_id=delivery_id,
    )
