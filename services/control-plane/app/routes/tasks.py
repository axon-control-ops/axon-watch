"""HTTP routes for the Gate 4 durable task ledger."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.persistence import task_store

router = APIRouter(tags=["tasks"])


class TaskCreateRequest(BaseModel):
    goal: str = Field(min_length=1)
    acceptance_criteria: str = ""
    risk: str = "normal"
    owner_role: str = ""
    dependencies: list[str] = Field(default_factory=list)
    exclusive_paths: list[str] = Field(default_factory=list)
    allowed_paths: list[str] = Field(default_factory=list)
    attempt_budget: int = Field(default=task_store.DEFAULT_ATTEMPT_BUDGET, ge=1, le=32)


class TaskLeaseRequest(BaseModel):
    lease_holder: str = Field(min_length=1)
    lease_seconds: int = Field(default=task_store.DEFAULT_LEASE_SECONDS, ge=30, le=86_400)
    run_id: str | None = None


class TaskCompleteRequest(BaseModel):
    terminal_outcome: str = "completed"
    run_id: str | None = None


class TaskFailRequest(BaseModel):
    terminal_outcome: str = "failed"
    run_id: str | None = None
    reopen_if_budget_remaining: bool = True


class TaskCancelRequest(BaseModel):
    terminal_outcome: str = "cancelled"


def _http_error(exc: task_store.TaskLedgerError) -> HTTPException:
    detail = str(exc)
    lowered = detail.lower()
    if "not found" in lowered:
        return HTTPException(status_code=404, detail=detail)
    if "already leased" in lowered or "attempt budget" in lowered or "terminal" in lowered:
        return HTTPException(status_code=409, detail=detail)
    if "dependency" in lowered:
        return HTTPException(status_code=409, detail=detail)
    return HTTPException(status_code=400, detail=detail)


@router.get("/api/workspaces/{workspace_id}/tasks")
def list_workspace_tasks(
    workspace_id: str,
    status: str | None = None,
    owner_role: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    try:
        items = task_store.list_tasks(
            workspace_id=workspace_id,
            status=status,
            owner_role=owner_role,
            limit=limit,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc
    return {"workspace_id": workspace_id, "items": items}


@router.post("/api/workspaces/{workspace_id}/tasks")
def create_workspace_task(workspace_id: str, body: TaskCreateRequest) -> dict[str, Any]:
    try:
        return task_store.create_task(
            workspace_id=workspace_id,
            goal=body.goal,
            acceptance_criteria=body.acceptance_criteria,
            risk=body.risk,
            owner_role=body.owner_role,
            dependencies=body.dependencies,
            exclusive_paths=body.exclusive_paths,
            allowed_paths=body.allowed_paths,
            attempt_budget=body.attempt_budget,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc


@router.get("/api/tasks/{task_id}")
def get_task(task_id: str) -> dict[str, Any]:
    record = task_store.get_task(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"task not found: {task_id}")
    return record


@router.post("/api/tasks/{task_id}/lease")
def lease_task(task_id: str, body: TaskLeaseRequest) -> dict[str, Any]:
    try:
        return task_store.lease_task(
            task_id,
            lease_holder=body.lease_holder,
            lease_seconds=body.lease_seconds,
            run_id=body.run_id,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc


@router.post("/api/tasks/{task_id}/renew-lease")
def renew_task_lease(task_id: str, body: TaskLeaseRequest) -> dict[str, Any]:
    try:
        return task_store.renew_lease(
            task_id,
            lease_holder=body.lease_holder,
            lease_seconds=body.lease_seconds,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc


@router.post("/api/tasks/{task_id}/complete")
def complete_task(task_id: str, body: TaskCompleteRequest) -> dict[str, Any]:
    try:
        return task_store.complete_task(
            task_id,
            terminal_outcome=body.terminal_outcome,
            run_id=body.run_id,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc


@router.post("/api/tasks/{task_id}/fail")
def fail_task(task_id: str, body: TaskFailRequest) -> dict[str, Any]:
    try:
        return task_store.fail_task(
            task_id,
            terminal_outcome=body.terminal_outcome,
            run_id=body.run_id,
            reopen_if_budget_remaining=body.reopen_if_budget_remaining,
        )
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc


@router.post("/api/tasks/{task_id}/cancel")
def cancel_task(task_id: str, body: TaskCancelRequest | None = None) -> dict[str, Any]:
    payload = body or TaskCancelRequest()
    try:
        cancelled = task_store.cancel_task(task_id, terminal_outcome=payload.terminal_outcome)
    except task_store.TaskLedgerError as exc:
        raise _http_error(exc) from exc
    run_id = str(cancelled.get("run_id") or "").strip()
    if run_id:
        try:
            from app.runs.restart_reconcile import interrupt_run_on_restart

            interrupt_run_on_restart(run_id)
        except Exception:  # noqa: BLE001 — task cancel must succeed even if run is already terminal
            pass
    return cancelled


class TaskCancelBatchRequest(BaseModel):
    task_ids: list[str] = Field(default_factory=list)
    scope: str = ""  # "waiting" = all open tasks in workspace
    terminal_outcome: str = "cancelled by operator"


@router.post("/api/workspaces/{workspace_id}/tasks/cancel-batch")
def cancel_tasks_batch(workspace_id: str, body: TaskCancelBatchRequest) -> dict[str, Any]:
    workspace = workspace_id.strip()
    if not workspace:
        raise HTTPException(status_code=400, detail="workspace_id is required")
    outcome = (body.terminal_outcome or "cancelled by operator").strip() or "cancelled by operator"
    target_ids: list[str] = []
    scope = (body.scope or "").strip().lower()
    if scope == "waiting":
        for row in task_store.list_tasks(workspace_id=workspace, limit=500):
            if str(row.get("status") or "").strip().lower() == "open":
                task_id = str(row.get("task_id") or "").strip()
                if task_id:
                    target_ids.append(task_id)
    else:
        target_ids = [str(item).strip() for item in body.task_ids if str(item).strip()]
    cancelled: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for task_id in target_ids:
        try:
            cancelled.append(cancel_task(task_id, TaskCancelRequest(terminal_outcome=outcome)))
        except HTTPException as exc:
            errors.append({"task_id": task_id, "detail": str(exc.detail)})
    return {
        "workspace_id": workspace,
        "cancelled_count": len(cancelled),
        "cancelled": cancelled,
        "errors": errors,
    }
