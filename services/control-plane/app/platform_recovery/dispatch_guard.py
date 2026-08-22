"""Duplicate-dispatch guard: one live worker per task/run."""

from __future__ import annotations

from typing import Any

from app.domain.run_state import is_terminal_phase
from app.persistence import run_store, task_store


class DuplicateDispatchError(RuntimeError):
    """A second worker would overlap an existing lease, run, or in-memory claim."""


def assert_dispatch_allowed(
    *,
    task_id: str | None,
    run_id: str,
    active_run_ids: set[str] | None = None,
    active_task_ids: dict[str, str] | None = None,
) -> None:
    cleaned_run = str(run_id or "").strip()
    if not cleaned_run:
        raise DuplicateDispatchError("run_id is required")
    if active_run_ids is not None and cleaned_run in active_run_ids:
        raise DuplicateDispatchError(f"run already has an in-memory worker: {cleaned_run}")

    cleaned_task = str(task_id or "").strip()
    if cleaned_task and active_task_ids is not None and cleaned_task in active_task_ids:
        owner = active_task_ids[cleaned_task]
        if owner != cleaned_run:
            raise DuplicateDispatchError(
                f"task {cleaned_task} already dispatched to run {owner}"
            )

    if cleaned_task:
        task = task_store.get_task(cleaned_task)
        if task is None:
            raise DuplicateDispatchError(f"task not found: {cleaned_task}")
        status = str(task.get("status") or "").strip()
        holder_run = str(task.get("run_id") or "").strip()
        if status == "leased" and holder_run and holder_run != cleaned_run:
            other = run_store.get_run(holder_run)
            if other is not None and not is_terminal_phase(str(other.get("phase") or "")):
                raise DuplicateDispatchError(
                    f"task {cleaned_task} is leased to live run {holder_run}"
                )

    record = run_store.get_run(cleaned_run)
    if record is None:
        return
    linked = str(record.get("task_id") or "").strip()
    if linked and cleaned_task and linked != cleaned_task:
        raise DuplicateDispatchError("run/task identity mismatch")


def existing_live_run_for_task(task_id: str) -> dict[str, Any] | None:
    cleaned = str(task_id or "").strip()
    if not cleaned:
        return None
    task = task_store.get_task(cleaned)
    if task is None:
        return None
    run_id = str(task.get("run_id") or "").strip()
    if not run_id:
        return None
    record = run_store.get_run(run_id)
    if record is None or is_terminal_phase(str(record.get("phase") or "")):
        return None
    return record
