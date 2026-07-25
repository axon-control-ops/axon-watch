"""Gate 6 acceptance-gated run lifecycle transitions."""

from __future__ import annotations

from typing import Any


def enforce_acceptance_for_executing_complete(record: dict[str, Any], run_id: str) -> None:
    """Block complete from executing when a leased worker lacks passing acceptance evidence."""
    if record["phase"] != "executing":
        return
    from app.workspace_agents.verifier_contract import enforce_acceptance_for_publish

    enforce_acceptance_for_publish(run_id)


def mark_review_ready(run_id: str) -> dict[str, Any]:
    from app.persistence import run_store
    from app.runs.service import RunLifecycleError, RunNotFoundError, _transition_record
    from app.workspace_agents.verifier_contract import enforce_acceptance_for_publish

    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")

    if record["phase"] != "executing":
        raise RunLifecycleError(
            f"review_ready requires executing phase, found {record['phase']}",
        )

    enforce_acceptance_for_publish(run_id)

    reviewed = _transition_record(
        record,
        to_phase="review_ready",
        current_step="Awaiting operator review",
        actor="control-plane",
        receipt_type="review_ready",
        receipt_summary="Active execution stopped; run awaiting operator review",
    )
    try:
        from app.runs.run_material_change import notify_run_material_change

        notify_run_material_change(run_id, reviewed)
    except Exception:
        pass
    return reviewed
