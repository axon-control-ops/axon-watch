"""Gate 6 — mandatory acceptance evidence before worker publish surfaces.

Workers (runs bound to a task_id) cannot reach review_ready or complete from
executing without a passing acceptance_evidence receipt. Operator thin-slice
runs without a task_id keep the prior lifecycle (Gate 6 focuses on leased work).
"""

from __future__ import annotations

from typing import Any

from app.persistence import run_store

ACCEPTANCE_RECEIPT_TYPE = "acceptance_evidence"
ACCEPTANCE_PASS_MARKER = "acceptance=pass"
ACCEPTANCE_FAIL_MARKER = "acceptance=fail"


def record_acceptance_evidence(
    run_id: str,
    *,
    passed: bool,
    summary: str,
    actor: str = "verifier",
) -> dict[str, Any]:
    """Persist a machine-checkable acceptance receipt on the run history."""
    from app.runs.service import append_run_execution_receipt

    marker = ACCEPTANCE_PASS_MARKER if passed else ACCEPTANCE_FAIL_MARKER
    cleaned = " ".join(str(summary or "").split()) or "acceptance evidence"
    return append_run_execution_receipt(
        run_id,
        receipt_type=ACCEPTANCE_RECEIPT_TYPE,
        receipt_summary=f"{marker} · {cleaned}",
        actor=actor,
        success=passed,
        intent="gate6_acceptance",
    )


def latest_acceptance_evidence(run_id: str) -> dict[str, Any] | None:
    from app.runs.service import RunNotFoundError

    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")
    history = run_store.list_history(str(record["history_ref"]))
    for entry in reversed(history):
        receipt = entry.get("receipt") if isinstance(entry, dict) else None
        if not isinstance(receipt, dict):
            continue
        if str(receipt.get("type") or "") != ACCEPTANCE_RECEIPT_TYPE:
            continue
        return {
            "receipt": receipt,
            "entry": entry,
            "passed": ACCEPTANCE_PASS_MARKER in str(receipt.get("summary") or ""),
        }
    return None


def has_passing_acceptance_evidence(run_id: str) -> bool:
    latest = latest_acceptance_evidence(run_id)
    return bool(latest and latest.get("passed"))


def require_acceptance_evidence(run_id: str) -> None:
    """Fail closed when a worker run lacks a passing acceptance receipt."""
    from app.runs.service import RunLifecycleError

    latest = latest_acceptance_evidence(run_id)
    if latest is None:
        raise RunLifecycleError(
            "review_ready/complete blocked: missing acceptance_evidence receipt (Gate 6)",
        )
    if not latest.get("passed"):
        raise RunLifecycleError(
            "review_ready/complete blocked: acceptance_evidence did not pass (Gate 6)",
        )


def run_requires_acceptance_evidence(record: dict[str, Any] | None) -> bool:
    if not isinstance(record, dict):
        return False
    return bool(str(record.get("task_id") or "").strip())


def enforce_acceptance_for_publish(run_id: str) -> None:
    from app.runs.service import get_run

    record = get_run(run_id)
    if run_requires_acceptance_evidence(record):
        require_acceptance_evidence(run_id)
