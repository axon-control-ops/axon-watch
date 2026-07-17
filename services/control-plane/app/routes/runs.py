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
    get_run,
    get_run_history,
    list_runs,
    mark_review_ready,
    reject_run,
    resume_run,
    stop_run,
)

router = APIRouter()


@router.get("/api/runs")
def runs_index() -> dict[str, Any]:
    items = list_runs()
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
