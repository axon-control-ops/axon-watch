"""Advance queued / starting runs into executing for worker dispatch."""

from __future__ import annotations

from typing import Any

from app.persistence import run_store
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    _apply_capabilities,
    _transition_record,
)


def begin_execution(
    run_id: str,
    *,
    actor: str = "control-plane",
    receipt_summary: str = "Queued run entered execution",
) -> dict[str, Any]:
    """Advance a queued/starting run into executing (scheduler / fan-out dispatch)."""
    record = run_store.get_run(run_id)
    if record is None:
        raise RunNotFoundError(f"run not found: {run_id}")
    phase = str(record.get("phase") or "").strip()
    if phase == "executing":
        return _apply_capabilities(record)
    if phase == "queued":
        record = _transition_record(
            record,
            to_phase="starting",
            current_step="Preparing run resources",
            actor=actor,
            receipt_type="system_transition",
            receipt_summary="Queued run accepted for dispatch",
        )
        phase = "starting"
    if phase != "starting":
        raise RunLifecycleError(
            f"begin_execution requires queued or starting phase, found {phase}",
        )
    return _transition_record(
        record,
        to_phase="executing",
        current_step="Executing thin-slice work",
        actor=actor,
        receipt_type="system_transition",
        receipt_summary=receipt_summary,
    )


__all__ = ["begin_execution"]
