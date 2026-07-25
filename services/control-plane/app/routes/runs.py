"""Run lifecycle CRUD routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.routes.schemas import CreateRunRequest
from app.runs.service import (
    RunLifecycleError,
    RunNotFoundError,
    approve_run,
    complete_run,
    create_run,
    drain_terminal_employee_runs,
    employee_run_retention_per_role,
    employee_run_stale_seconds,
    get_run,
    get_run_history,
    list_operator_facing_runs,
    list_runs,
    mark_review_ready,
    reap_abandoned_review_ready_runs,
    reap_stale_employee_runs,
    reject_run,
    resume_run,
    review_ready_stale_seconds,
    stop_run,
)

router = APIRouter()


@router.get("/api/runs")
def runs_index(operator_facing: bool = False) -> dict[str, Any]:
    items = list_operator_facing_runs() if operator_facing else list_runs()
    return {"items": items, "count": len(items)}


@router.post("/api/runs")
def runs_create(body: CreateRunRequest) -> dict[str, Any]:
    return create_run(
        workspace_id=body.workspace_id,
        mode=body.mode,
        summary=body.summary,
        detail=body.detail,
        requires_approval=body.requires_approval,
        employee_role=body.employee_role,
    )


@router.post("/api/runs/reconcile-stale")
def runs_reconcile_stale() -> dict[str, Any]:
    """Fail/cancel idle role-tagged worker runs beyond the stale TTL."""
    reaped = reap_stale_employee_runs()
    return {
        "reaped_run_ids": reaped,
        "count": len(reaped),
        "stale_seconds": employee_run_stale_seconds(),
    }


@router.post("/api/runs/prune-employee-history")
def runs_prune_employee_history() -> dict[str, Any]:
    """Drain terminal role-tagged runs beyond the per-role retention window."""
    pruned = drain_terminal_employee_runs()
    return {
        "pruned_run_ids": pruned,
        "count": len(pruned),
        "keep_per_role": employee_run_retention_per_role(),
    }


@router.post("/api/runs/reconcile-review-ready")
def runs_reconcile_review_ready() -> dict[str, Any]:
    """Complete abandoned untagged review_ready checkpoints beyond the idle TTL."""
    completed = reap_abandoned_review_ready_runs()
    return {
        "completed_run_ids": completed,
        "count": len(completed),
        "stale_seconds": review_ready_stale_seconds(),
    }


@router.get("/api/runs/{run_id}")
def runs_show(run_id: str) -> dict[str, Any]:
    try:
        return get_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/api/runs/{run_id}/history")
def runs_history(run_id: str) -> dict[str, Any]:
    try:
        return get_run_history(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/complete")
def runs_complete(run_id: str) -> dict[str, Any]:
    try:
        return complete_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/review-ready")
def runs_review_ready(run_id: str) -> dict[str, Any]:
    try:
        return mark_review_ready(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/stop")
def runs_stop(run_id: str) -> dict[str, Any]:
    try:
        return stop_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/resume")
def runs_resume(run_id: str) -> dict[str, Any]:
    try:
        return resume_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/approve")
def runs_approve(run_id: str) -> dict[str, Any]:
    try:
        return approve_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/runs/{run_id}/reject")
def runs_reject(run_id: str) -> dict[str, Any]:
    try:
        return reject_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
