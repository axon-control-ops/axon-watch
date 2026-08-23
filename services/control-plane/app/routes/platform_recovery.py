"""Recovery Center, doctor, instructions, and reconcile HTTP API."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.platform_recovery.agent_health import score_agent_health
from app.platform_recovery.autonomy import autonomy_label, configured_autonomy_level
from app.platform_recovery.checkpoints import get_checkpoint
from app.platform_recovery.circuit_breaker import list_circuits
from app.platform_recovery.doctor import run_doctor
from app.platform_recovery.instructions import build_operational_instructions
from app.platform_recovery.lessons import list_lessons, record_lesson
from app.platform_recovery.projection import build_recovery_center
from app.platform_recovery.reconcile_artifacts import execute_reconcile, preview_reconcile
from app.platform_recovery.restart import preview_restart_impact
from app.platform_recovery.store import acknowledge_recovery
from app.runs.service import RunLifecycleError, RunNotFoundError, resume_run

router = APIRouter(tags=["platform-recovery"])


class InstructionsRequest(BaseModel):
    workspace_id: str = Field(min_length=1)
    run_id: str | None = None
    agent: str | None = None


class LessonRequest(BaseModel):
    failure_class: str
    root_cause: str
    recovery: str
    verification: str
    confidence: str = "low"
    provenance_run_id: str = ""
    verified: bool = False


class ReconcileRequest(BaseModel):
    execute: bool = False
    approve_worktree_delete: bool = False


@router.get("/api/recovery/center")
def recovery_center(workspace_id: str | None = None) -> dict[str, Any]:
    return build_recovery_center(workspace_id=workspace_id)


@router.get("/api/recovery/circuits")
def recovery_circuits() -> dict[str, Any]:
    return {"items": list_circuits()}


@router.get("/api/recovery/health")
def recovery_agent_health(workspace_id: str | None = None, role: str | None = None) -> dict[str, Any]:
    return score_agent_health(workspace_id=workspace_id, role=role)


@router.get("/api/platform/doctor")
def platform_doctor() -> dict[str, Any]:
    return run_doctor()


@router.get("/api/recovery/restart-preview")
def recovery_restart_preview() -> dict[str, Any]:
    return preview_restart_impact()


@router.get("/api/platform/autonomy")
def platform_autonomy() -> dict[str, Any]:
    level = configured_autonomy_level()
    return {"level": level, "label": autonomy_label(level)}


@router.post("/api/recovery/instructions")
def recovery_instructions(body: InstructionsRequest) -> dict[str, Any]:
    content = build_operational_instructions(
        workspace_id=body.workspace_id,
        run_id=body.run_id,
        agent=body.agent,
    )
    return {"content": content, "runtime_label": "live-state", "fallback": False}


@router.post("/api/recovery/{recovery_id}/acknowledge")
def recovery_acknowledge(recovery_id: str) -> dict[str, Any]:
    record = acknowledge_recovery(recovery_id)
    if record is None:
        raise HTTPException(status_code=404, detail="recovery record not found")
    return record


@router.post("/api/recovery/runs/{run_id}/resume")
def recovery_resume_run(run_id: str) -> dict[str, Any]:
    checkpoint = get_checkpoint(run_id)
    try:
        resumed = resume_run(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RunLifecycleError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"run": resumed, "checkpoint": checkpoint}


@router.post("/api/platform/reconcile")
def platform_reconcile(body: ReconcileRequest) -> dict[str, Any]:
    if body.execute:
        return execute_reconcile(approve_worktree_delete=body.approve_worktree_delete)
    return preview_reconcile()


@router.get("/api/recovery/lessons")
def recovery_lessons(failure_class: str | None = None) -> dict[str, Any]:
    return {"items": list_lessons(failure_class=failure_class)}


@router.post("/api/recovery/lessons")
def recovery_lessons_create(body: LessonRequest) -> dict[str, Any]:
    return record_lesson(
        failure_class=body.failure_class,
        root_cause=body.root_cause,
        recovery=body.recovery,
        verification=body.verification,
        confidence=body.confidence,
        provenance_run_id=body.provenance_run_id,
        verified=body.verified,
    )
