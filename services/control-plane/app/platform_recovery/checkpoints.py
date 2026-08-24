"""Task/run checkpoints. Never store secrets."""

from __future__ import annotations

import json
from typing import Any

from app.platform_recovery.store import managed_connection, utc_now_iso

_CHECKPOINT_KEYS = (
    "mission_id",
    "task_id",
    "worker_id",
    "workspace_id",
    "branch",
    "worktree",
    "current_stage",
    "last_verified_stage",
    "attempt_number",
    "remaining_attempt_budget",
    "execution_provider",
    "execution_context_reference",
    "verification_state",
    "recovery_state",
)

_SECRET_KEYS = {"token", "password", "secret", "api_key", "authorization"}


def _clean_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key in _CHECKPOINT_KEYS:
        value = payload.get(key)
        if isinstance(value, str) and key.lower() in _SECRET_KEYS:
            continue
        if key in {"attempt_number", "remaining_attempt_budget"}:
            try:
                cleaned[key] = int(value or 0)
            except (TypeError, ValueError):
                cleaned[key] = 0
        else:
            cleaned[key] = str(value or "")
    paths = payload.get("changed_paths") or []
    if not isinstance(paths, list):
        paths = []
    cleaned["changed_paths"] = [str(item) for item in paths if str(item).strip()][:200]
    return cleaned


def write_checkpoint(run_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = str(run_id or "").strip()
    if not cleaned:
        raise ValueError("run_id is required")
    body = _clean_payload(payload)
    now = utc_now_iso()
    progress_at = str(payload.get("last_meaningful_progress_at") or now)
    with managed_connection() as conn:
        conn.execute(
            """
            INSERT INTO run_checkpoints (
                run_id, mission_id, task_id, worker_id, workspace_id, branch, worktree,
                current_stage, last_verified_stage, last_checkpoint_at,
                last_meaningful_progress_at, attempt_number, remaining_attempt_budget,
                execution_provider, execution_context_reference, changed_paths_json,
                verification_state, recovery_state
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(run_id) DO UPDATE SET
                mission_id=excluded.mission_id,
                task_id=excluded.task_id,
                worker_id=excluded.worker_id,
                workspace_id=excluded.workspace_id,
                branch=excluded.branch,
                worktree=excluded.worktree,
                current_stage=excluded.current_stage,
                last_verified_stage=excluded.last_verified_stage,
                last_checkpoint_at=excluded.last_checkpoint_at,
                last_meaningful_progress_at=excluded.last_meaningful_progress_at,
                attempt_number=excluded.attempt_number,
                remaining_attempt_budget=excluded.remaining_attempt_budget,
                execution_provider=excluded.execution_provider,
                execution_context_reference=excluded.execution_context_reference,
                changed_paths_json=excluded.changed_paths_json,
                verification_state=excluded.verification_state,
                recovery_state=excluded.recovery_state
            """,
            (
                cleaned,
                body["mission_id"],
                body["task_id"],
                body["worker_id"],
                body["workspace_id"],
                body["branch"],
                body["worktree"],
                body["current_stage"],
                body["last_verified_stage"],
                now,
                progress_at,
                body["attempt_number"] or 1,
                body["remaining_attempt_budget"],
                body["execution_provider"],
                body["execution_context_reference"],
                json.dumps(body["changed_paths"], separators=(",", ":")),
                body["verification_state"],
                body["recovery_state"],
            ),
        )
        conn.commit()
    record = get_checkpoint(cleaned)
    assert record is not None
    return record


def touch_meaningful_progress(run_id: str, *, stage: str = "", provider: str = "") -> dict[str, Any]:
    existing = get_checkpoint(run_id) or {"run_id": run_id}
    existing["current_stage"] = stage or existing.get("current_stage") or "executing"
    existing["execution_provider"] = provider or existing.get("execution_provider") or ""
    existing["last_meaningful_progress_at"] = utc_now_iso()
    return write_checkpoint(run_id, existing)


def get_checkpoint(run_id: str) -> dict[str, Any] | None:
    cleaned = str(run_id or "").strip()
    if not cleaned:
        return None
    with managed_connection() as conn:
        row = conn.execute(
            "SELECT * FROM run_checkpoints WHERE run_id = ?",
            (cleaned,),
        ).fetchone()
    if row is None:
        return None
    paths = []
    try:
        parsed = json.loads(str(row["changed_paths_json"] or "[]"))
        if isinstance(parsed, list):
            paths = [str(item) for item in parsed]
    except json.JSONDecodeError:
        paths = []
    return {
        "run_id": row["run_id"],
        "mission_id": row["mission_id"],
        "task_id": row["task_id"],
        "worker_id": row["worker_id"],
        "workspace_id": row["workspace_id"],
        "branch": row["branch"],
        "worktree": row["worktree"],
        "current_stage": row["current_stage"],
        "last_verified_stage": row["last_verified_stage"],
        "last_checkpoint_at": row["last_checkpoint_at"],
        "last_meaningful_progress_at": row["last_meaningful_progress_at"],
        "attempt_number": int(row["attempt_number"] or 1),
        "remaining_attempt_budget": int(row["remaining_attempt_budget"] or 0),
        "execution_provider": row["execution_provider"],
        "execution_context_reference": row["execution_context_reference"],
        "changed_paths": paths,
        "verification_state": row["verification_state"],
        "recovery_state": row["recovery_state"],
    }


def checkpoint_is_valid(record: dict[str, Any] | None) -> bool:
    if not record:
        return False
    if not str(record.get("run_id") or "").strip():
        return False
    if not str(record.get("last_checkpoint_at") or "").strip():
        return False
    worktree = str(record.get("worktree") or "").strip()
    if worktree:
        from pathlib import Path

        path = Path(worktree)
        if not path.exists():
            return False
    return True
