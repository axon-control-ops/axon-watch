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


@dataclass(frozen=True)
class IngestResult:
    accepted: bool
    reason: str
    dedupe_key: str = ""
    task_id: str = ""
    run_id: str = ""
    signal_id: str = ""
    duplicate: bool = False


def ingest_workflow_run_event(
    payload: dict[str, Any],
    *,
    dispatch: bool | None = None,
) -> IngestResult:
    classified = classify_workflow_run_event(payload)
    if classified is None:
        return IngestResult(accepted=False, reason="not_a_completed_failure")

    binding = match_binding(
        github_owner=classified["github_owner"],
        github_repo=classified["github_repo"],
        workflow_name=classified["workflow_name"],
        enabled_only=True,
    )
    if binding is None:
        return IngestResult(accepted=False, reason="no_enabled_binding")

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
    )
