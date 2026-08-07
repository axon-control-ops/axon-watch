"""Durable workspace task ledger (Gate 4) — leased, attempt-bounded work units."""

from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import os
import uuid
from typing import Any, Iterable

from app.persistence import run_store_sqlite

TASK_STATUSES = frozenset({"open", "leased", "completed", "failed", "cancelled"})
DEFAULT_ATTEMPT_BUDGET = 3
DEFAULT_LEASE_SECONDS = 3600

_TASK_COLUMNS = (
    "task_id",
    "workspace_id",
    "goal",
    "acceptance_criteria",
    "risk",
    "owner_role",
    "dependencies_json",
    "exclusive_paths_json",
    "allowed_paths_json",
    "approval_receipt_id",
    "status",
    "lease_holder",
    "lease_expires_at",
    "attempt_budget",
    "attempts_used",
    "terminal_outcome",
    "run_id",
    "created_at",
    "updated_at",
)


class TaskLedgerError(ValueError):
    """Domain error for task create/lease/complete flows."""


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        yield connection
    finally:
        connection.close()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc_now_iso() -> str:
    return _utc_now().isoformat().replace("+00:00", "Z")


def _parse_iso(value: str | None) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def ensure_task_ledger_schema(connection: Any) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_tasks (
            task_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            goal TEXT NOT NULL,
            acceptance_criteria TEXT NOT NULL DEFAULT '',
            risk TEXT NOT NULL DEFAULT 'normal',
            owner_role TEXT NOT NULL DEFAULT '',
            dependencies_json TEXT NOT NULL DEFAULT '[]',
            exclusive_paths_json TEXT NOT NULL DEFAULT '[]',
            allowed_paths_json TEXT NOT NULL DEFAULT '[]',
            approval_receipt_id TEXT,
            status TEXT NOT NULL,
            lease_holder TEXT,
            lease_expires_at TEXT,
            attempt_budget INTEGER NOT NULL DEFAULT 3,
            attempts_used INTEGER NOT NULL DEFAULT 0,
            terminal_outcome TEXT,
            run_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(workspace_tasks)").fetchall()
    }
    if "exclusive_paths_json" not in columns:
        connection.execute(
            "ALTER TABLE workspace_tasks "
            "ADD COLUMN exclusive_paths_json TEXT NOT NULL DEFAULT '[]'"
        )
    if "allowed_paths_json" not in columns:
        connection.execute(
            "ALTER TABLE workspace_tasks "
            "ADD COLUMN allowed_paths_json TEXT NOT NULL DEFAULT '[]'"
        )
    if "approval_receipt_id" not in columns:
        connection.execute(
            "ALTER TABLE workspace_tasks ADD COLUMN approval_receipt_id TEXT"
        )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_tasks_workspace_status
            ON workspace_tasks(workspace_id, status, updated_at DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_tasks_lease
            ON workspace_tasks(status, lease_expires_at)
        """
    )
    connection.commit()


def _parse_path_list(raw: Any) -> list[str]:
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _row_to_record(row: Any) -> dict[str, Any]:
    dependencies_raw = row["dependencies_json"] if "dependencies_json" in row.keys() else "[]"
    exclusive_paths_raw = (
        row["exclusive_paths_json"] if "exclusive_paths_json" in row.keys() else "[]"
    )
    allowed_paths_raw = (
        row["allowed_paths_json"] if "allowed_paths_json" in row.keys() else "[]"
    )
    dependencies = _parse_path_list(dependencies_raw)
    exclusive_paths = _parse_path_list(exclusive_paths_raw)
    allowed_paths = _parse_path_list(allowed_paths_raw)
    return {
        "task_id": row["task_id"],
        "workspace_id": row["workspace_id"],
        "goal": row["goal"],
        "acceptance_criteria": row["acceptance_criteria"] or "",
        "risk": row["risk"] or "normal",
        "owner_role": row["owner_role"] or "",
        "dependencies": dependencies,
        "exclusive_paths": exclusive_paths,
        "allowed_paths": allowed_paths,
        "approval_receipt_id": (
            row["approval_receipt_id"]
            if "approval_receipt_id" in row.keys()
            else None
        ),
        "status": row["status"],
        "lease_holder": row["lease_holder"],
        "lease_expires_at": row["lease_expires_at"],
        "attempt_budget": int(row["attempt_budget"] or DEFAULT_ATTEMPT_BUDGET),
        "attempts_used": int(row["attempts_used"] or 0),
        "terminal_outcome": row["terminal_outcome"],
        "run_id": row["run_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def reset_store() -> None:
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        connection.execute("DELETE FROM workspace_tasks")
        connection.commit()


def get_task(task_id: str) -> dict[str, Any] | None:
    task_key = task_id.strip()
    if not task_key:
        return None
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        row = connection.execute(
            "SELECT * FROM workspace_tasks WHERE task_id = ?",
            (task_key,),
        ).fetchone()
    return _row_to_record(row) if row else None


def list_tasks(
    *,
    workspace_id: str,
    status: str | None = None,
    owner_role: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    workspace = workspace_id.strip()
    if not workspace:
        return []
    clauses = ["workspace_id = ?"]
    params: list[Any] = [workspace]
    status_filter = (status or "").strip().lower()
    if status_filter:
        if status_filter not in TASK_STATUSES:
            raise TaskLedgerError(f"invalid task status filter: {status_filter}")
        clauses.append("status = ?")
        params.append(status_filter)
    role_filter = (owner_role or "").strip().lower()
    if role_filter:
        clauses.append("lower(owner_role) = ?")
        params.append(role_filter)
    bound = max(1, min(int(limit), 500))
    params.append(bound)
    sql = f"""
        SELECT * FROM workspace_tasks
        WHERE {' AND '.join(clauses)}
        ORDER BY updated_at DESC, task_id ASC
        LIMIT ?
    """
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        rows = connection.execute(sql, tuple(params)).fetchall()
    return [_row_to_record(row) for row in rows]


def create_task(
    *,
    workspace_id: str,
    goal: str,
    acceptance_criteria: str = "",
    risk: str = "normal",
    owner_role: str = "",
    dependencies: list[str] | None = None,
    exclusive_paths: list[str] | None = None,
    allowed_paths: list[str] | None = None,
    approval_receipt_id: str | None = None,
    attempt_budget: int = DEFAULT_ATTEMPT_BUDGET,
) -> dict[str, Any]:
    workspace = workspace_id.strip()
    goal_text = goal.strip()
    if not workspace:
        raise TaskLedgerError("workspace_id is required")
    if not goal_text:
        raise TaskLedgerError("goal is required")
    budget = max(1, min(int(attempt_budget), 32))
    deps = [str(item).strip() for item in (dependencies or []) if str(item).strip()]
    paths = [str(item).strip() for item in (exclusive_paths or []) if str(item).strip()]
    allowed = [str(item).strip() for item in (allowed_paths or []) if str(item).strip()]
    if not allowed and owner_role.strip():
        # Unset scope is fail-closed downstream and would leave the task unable
        # to write anything at all — see default_write_scope_for_role.
        from app.workspace_agents.execution_policy import default_write_scope_for_role

        allowed = default_write_scope_for_role(owner_role)
    from app.workspace_agents.autonomous_attention_policy import normalize_task_risk

    timestamp = _utc_now_iso()
    record = {
        "task_id": f"task-{uuid.uuid4().hex[:16]}",
        "workspace_id": workspace,
        "goal": goal_text,
        "acceptance_criteria": acceptance_criteria.strip(),
        "risk": normalize_task_risk(risk),
        "owner_role": owner_role.strip().lower(),
        "dependencies_json": json.dumps(deps),
        "exclusive_paths_json": json.dumps(paths),
        "allowed_paths_json": json.dumps(allowed),
        "approval_receipt_id": (
            str(approval_receipt_id).strip() if approval_receipt_id else None
        ),
        "status": "open",
        "lease_holder": None,
        "lease_expires_at": None,
        "attempt_budget": budget,
        "attempts_used": 0,
        "terminal_outcome": None,
        "run_id": None,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        placeholders = ", ".join("?" for _ in _TASK_COLUMNS)
        connection.execute(
            f"""
            INSERT INTO workspace_tasks ({", ".join(_TASK_COLUMNS)})
            VALUES ({placeholders})
            """,
            tuple(record[column] for column in _TASK_COLUMNS),
        )
        connection.commit()
    stored = get_task(record["task_id"])
    assert stored is not None
    return stored


def _expire_stale_leases(connection: Any, *, now: datetime) -> None:
    now_iso = now.isoformat().replace("+00:00", "Z")
    rows = connection.execute(
        """
        SELECT task_id, lease_expires_at
        FROM workspace_tasks
        WHERE status = 'leased' AND lease_expires_at IS NOT NULL
        """
    ).fetchall()
    for row in rows:
        expires = _parse_iso(row["lease_expires_at"])
        if expires is None or expires > now:
            continue
        connection.execute(
            """
            UPDATE workspace_tasks
            SET status = 'open',
                lease_holder = NULL,
                lease_expires_at = NULL,
                run_id = NULL,
                updated_at = ?
            WHERE task_id = ? AND status = 'leased'
            """,
            (now_iso, row["task_id"]),
        )


def _dependency_ids(record: dict[str, Any]) -> list[str]:
    raw = record.get("dependencies")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    try:
        parsed = json.loads(str(record.get("dependencies_json") or "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [str(item).strip() for item in parsed if str(item).strip()]


def _assert_dependencies_satisfied(connection: Any, record: dict[str, Any]) -> None:
    deps = _dependency_ids(record)
    if not deps:
        return
    for dep_id in deps:
        row = connection.execute(
            "SELECT status FROM workspace_tasks WHERE task_id = ?",
            (dep_id,),
        ).fetchone()
        if row is None:
            raise TaskLedgerError(f"dependency missing: {dep_id}")
        status = str(row["status"] or "").strip().lower()
        if status != "completed":
            raise TaskLedgerError(f"dependency not completed: {dep_id} ({status or 'unknown'})")


def _normalized_exclusive_paths(record: dict[str, Any]) -> list[str]:
    raw = record.get("exclusive_paths")
    if not isinstance(raw, list):
        return []
    return [
        str(path).strip().strip("/").lower()
        for path in raw
        if str(path).strip().strip("/")
    ]


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _assert_no_exclusive_path_conflict(
    connection: Any,
    record: dict[str, Any],
) -> None:
    requested = _normalized_exclusive_paths(record)
    if not requested:
        return
    rows = connection.execute(
        """
        SELECT *
        FROM workspace_tasks
        WHERE workspace_id = ?
          AND status = 'leased'
          AND task_id != ?
        """,
        (record["workspace_id"], record["task_id"]),
    ).fetchall()
    for row in rows:
        active = _row_to_record(row)
        active_paths = _normalized_exclusive_paths(active)
        if any(_paths_overlap(left, right) for left in requested for right in active_paths):
            raise TaskLedgerError(
                "exclusive path conflict with leased task "
                f"{active['task_id']}"
            )


def lease_task(
    task_id: str,
    *,
    lease_holder: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    run_id: str | None = None,
) -> dict[str, Any]:
    task_key = task_id.strip()
    holder = lease_holder.strip()
    if not task_key:
        raise TaskLedgerError("task_id is required")
    if not holder:
        raise TaskLedgerError("lease_holder is required")
    ttl = max(30, min(int(lease_seconds), 24 * 3600))
    now = _utc_now()
    expires_iso = (now + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")
    updated_at = now.isoformat().replace("+00:00", "Z")

    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        _expire_stale_leases(connection, now=now)
        row = connection.execute(
            "SELECT * FROM workspace_tasks WHERE task_id = ?",
            (task_key,),
        ).fetchone()
        if row is None:
            raise TaskLedgerError(f"task not found: {task_key}")
        record = _row_to_record(row)
        if record["status"] in {"completed", "failed", "cancelled"}:
            raise TaskLedgerError(f"task is terminal ({record['status']})")
        if record["attempts_used"] >= record["attempt_budget"]:
            raise TaskLedgerError("attempt budget exhausted")
        if record["status"] == "leased":
            raise TaskLedgerError("task already leased")
        _assert_dependencies_satisfied(connection, record)
        _assert_no_exclusive_path_conflict(connection, record)

        next_attempts = int(record["attempts_used"]) + 1
        cursor = connection.execute(
            """
            UPDATE workspace_tasks
            SET status = 'leased',
                lease_holder = ?,
                lease_expires_at = ?,
                attempts_used = ?,
                run_id = ?,
                updated_at = ?
            WHERE task_id = ?
              AND status = 'open'
              AND attempts_used < attempt_budget
            """,
            (
                holder,
                expires_iso,
                next_attempts,
                (run_id or "").strip() or None,
                updated_at,
                task_key,
            ),
        )
        # `total_changes` is cumulative for the connection and also includes
        # `_expire_stale_leases` above. Use this UPDATE's rowcount so a stale
        # lease can expire and be reacquired atomically.
        if cursor.rowcount != 1:
            connection.rollback()
            raise TaskLedgerError("task already leased")
        connection.commit()

    leased = get_task(task_key)
    assert leased is not None
    return leased


def renew_lease(
    task_id: str,
    *,
    lease_holder: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    """Extend an active lease held by ``lease_holder`` (long-running dispatch)."""
    task_key = task_id.strip()
    holder = lease_holder.strip()
    if not task_key:
        raise TaskLedgerError("task_id is required")
    if not holder:
        raise TaskLedgerError("lease_holder is required")
    ttl = max(30, min(int(lease_seconds), 24 * 3600))
    now = _utc_now()
    expires_iso = (now + timedelta(seconds=ttl)).isoformat().replace("+00:00", "Z")
    updated_at = now.isoformat().replace("+00:00", "Z")
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        row = connection.execute(
            "SELECT * FROM workspace_tasks WHERE task_id = ?",
            (task_key,),
        ).fetchone()
        if row is None:
            raise TaskLedgerError(f"task not found: {task_key}")
        record = _row_to_record(row)
        if record["status"] != "leased":
            raise TaskLedgerError(f"task is not leased ({record['status']})")
        if str(record.get("lease_holder") or "").strip() != holder:
            raise TaskLedgerError("lease holder mismatch")
        connection.execute(
            """
            UPDATE workspace_tasks
            SET lease_expires_at = ?, updated_at = ?
            WHERE task_id = ? AND status = 'leased' AND lease_holder = ?
            """,
            (expires_iso, updated_at, task_key, holder),
        )
        if connection.total_changes != 1:
            connection.rollback()
            raise TaskLedgerError("failed to renew lease")
        connection.commit()
    renewed = get_task(task_key)
    assert renewed is not None
    return renewed


def complete_task(
    task_id: str,
    *,
    terminal_outcome: str = "completed",
    run_id: str | None = None,
) -> dict[str, Any]:
    return _finalize_task(
        task_id,
        status="completed",
        terminal_outcome=terminal_outcome or "completed",
        run_id=run_id,
    )


def fail_task(
    task_id: str,
    *,
    terminal_outcome: str = "failed",
    run_id: str | None = None,
    reopen_if_budget_remaining: bool = True,
) -> dict[str, Any]:
    task_key = task_id.strip()
    current = get_task(task_key)
    if current is None:
        raise TaskLedgerError(f"task not found: {task_key}")
    if current["status"] in {"completed", "cancelled"}:
        raise TaskLedgerError(f"task is terminal ({current['status']})")
    if (
        reopen_if_budget_remaining
        and current["attempts_used"] < current["attempt_budget"]
        and current["status"] == "leased"
    ):
        updated_at = _utc_now_iso()
        with _managed_connection() as connection:
            ensure_task_ledger_schema(connection)
            connection.execute(
                """
                UPDATE workspace_tasks
                SET status = 'open',
                    lease_holder = NULL,
                    lease_expires_at = NULL,
                    run_id = NULL,
                    terminal_outcome = ?,
                    updated_at = ?
                WHERE task_id = ? AND status = 'leased'
                """,
                ((terminal_outcome or "failed").strip() or "failed", updated_at, task_key),
            )
            connection.commit()
        reopened = get_task(task_key)
        assert reopened is not None
        return reopened
    return _finalize_task(
        task_id,
        status="failed",
        terminal_outcome=terminal_outcome or "failed",
        run_id=run_id,
    )


def cancel_task(task_id: str, *, terminal_outcome: str = "cancelled") -> dict[str, Any]:
    return _finalize_task(
        task_id,
        status="cancelled",
        terminal_outcome=terminal_outcome or "cancelled",
        run_id=None,
    )


def _finalize_task(
    task_id: str,
    *,
    status: str,
    terminal_outcome: str,
    run_id: str | None,
) -> dict[str, Any]:
    task_key = task_id.strip()
    if not task_key:
        raise TaskLedgerError("task_id is required")
    if status not in {"completed", "failed", "cancelled"}:
        raise TaskLedgerError(f"invalid terminal status: {status}")
    updated_at = _utc_now_iso()
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        row = connection.execute(
            "SELECT status FROM workspace_tasks WHERE task_id = ?",
            (task_key,),
        ).fetchone()
        if row is None:
            raise TaskLedgerError(f"task not found: {task_key}")
        current_status = str(row["status"] or "")
        if current_status in {"completed", "failed", "cancelled"} and current_status != status:
            raise TaskLedgerError(f"task is terminal ({current_status})")
        connection.execute(
            """
            UPDATE workspace_tasks
            SET status = ?,
                lease_holder = NULL,
                lease_expires_at = NULL,
                terminal_outcome = ?,
                run_id = COALESCE(?, run_id),
                updated_at = ?
            WHERE task_id = ?
            """,
            (
                status,
                terminal_outcome.strip() or status,
                (run_id or "").strip() or None,
                updated_at,
                task_key,
            ),
        )
        connection.commit()
    finalized = get_task(task_key)
    assert finalized is not None
    return deepcopy(finalized)


def bind_task_run(task_id: str, run_id: str) -> dict[str, Any]:
    """Attach a run_id to an already-leased task."""
    task_key = task_id.strip()
    run_key = run_id.strip()
    if not task_key:
        raise TaskLedgerError("task_id is required")
    if not run_key:
        raise TaskLedgerError("run_id is required")
    updated_at = _utc_now_iso()
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        connection.execute(
            """
            UPDATE workspace_tasks
            SET run_id = ?, updated_at = ?
            WHERE task_id = ? AND status = 'leased'
            """,
            (run_key, updated_at, task_key),
        )
        if connection.total_changes != 1:
            connection.rollback()
            raise TaskLedgerError(f"cannot bind run to task: {task_key}")
        connection.commit()
    bound = get_task(task_key)
    assert bound is not None
    return bound


def reopen_orphaned_leased_tasks(
    *,
    terminal_run_ids: Iterable[str],
    terminal_outcome: str = "run terminal; lease recovered",
    refund_attempts: bool = False,
) -> list[dict[str, Any]]:
    """Reopen leased tasks whose bound run already reached a terminal phase.
    Prevents canceled/failed/paused worker runs from leaving leased zombies that
    block claim_open_task_for_role until the lease TTL expires.
    """
    run_keys = {
        str(run_id).strip()
        for run_id in terminal_run_ids
        if str(run_id).strip()
    }
    if not run_keys:
        return []
    recovered: list[dict[str, Any]] = []
    updated_at = _utc_now_iso()
    outcome = (terminal_outcome or "run terminal; lease recovered").strip()
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        rows = connection.execute(
            """
            SELECT *
            FROM workspace_tasks
            WHERE status = 'leased'
              AND run_id IS NOT NULL
            """
        ).fetchall()
        for row in rows:
            record = _row_to_record(row)
            run_id = str(record.get("run_id") or "").strip()
            if run_id not in run_keys:
                continue
            connection.execute(
                """
                UPDATE workspace_tasks
                SET status = 'open',
                    lease_holder = NULL,
                    lease_expires_at = NULL,
                    attempts_used = MAX(0, attempts_used - ?),
                    run_id = NULL,
                    terminal_outcome = ?,
                    updated_at = ?
                WHERE task_id = ? AND status = 'leased'
                """,
                (int(refund_attempts), outcome, updated_at, record["task_id"]),
            )
            if connection.total_changes:
                recovered.append(
                    {
                        **record,
                        "status": "open",
                        "lease_holder": None,
                        "lease_expires_at": None,
                        "attempts_used": max(0, int(record["attempts_used"]) - int(refund_attempts)),
                        "run_id": None,
                        "terminal_outcome": outcome,
                        "updated_at": updated_at,
                    }
                )
        connection.commit()
    return recovered

def cancel_tasks_matching_goal_prefix(
    *,
    workspace_id: str,
    goal_substr: str,
    exclude_task_id: str | None = None,
    terminal_outcome: str = "superseded",
) -> list[dict[str, Any]]:
    """Cancel open/leased tasks whose goal contains ``goal_substr``."""
    workspace = workspace_id.strip()
    needle = goal_substr.strip().lower()
    if not workspace or not needle:
        return []
    exclude = (exclude_task_id or "").strip()
    cancelled: list[dict[str, Any]] = []
    for record in list_tasks(workspace_id=workspace, limit=500):
        status = str(record.get("status") or "").strip().lower()
        if status not in {"open", "leased"}:
            continue
        task_id = str(record.get("task_id") or "").strip()
        if exclude and task_id == exclude:
            continue
        goal = str(record.get("goal") or "").lower()
        if needle not in goal:
            continue
        try:
            cancelled.append(
                cancel_task(task_id, terminal_outcome=terminal_outcome)
            )
        except TaskLedgerError:
            continue
    return cancelled


def claim_open_task_for_role(
    *,
    workspace_id: str,
    owner_role: str,
    lease_holder: str,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    run_id: str | None = None,
) -> dict[str, Any] | None:
    """Lease the oldest open task for a role, or return None when none are available."""
    workspace = workspace_id.strip()
    role = owner_role.strip().lower()
    holder = lease_holder.strip()
    if not workspace or not role or not holder:
        return None
    with _managed_connection() as connection:
        ensure_task_ledger_schema(connection)
        _expire_stale_leases(connection, now=_utc_now())
        connection.commit()
        rows = connection.execute(
            """
            SELECT task_id
            FROM workspace_tasks
            WHERE workspace_id = ?
              AND status = 'open'
              AND lower(owner_role) = ?
              AND lower(risk) IN ('normal', 'low', 'approved')
              AND attempts_used < attempt_budget
            ORDER BY rowid ASC
            """,
            (workspace, role),
        ).fetchall()
    from app.workspace_agents.autonomous_attention_policy import task_allows_autonomous_lease

    for row in rows:
        task_key = str(row["task_id"] or "").strip()
        if not task_key:
            continue
        candidate = get_task(task_key)
        decision = task_allows_autonomous_lease(candidate)
        if decision.tier != "auto_safe" or decision.decision != "dispatch":
            continue
        try:
            return lease_task(
                task_key,
                lease_holder=holder,
                lease_seconds=lease_seconds,
                run_id=run_id,
            )
        except TaskLedgerError:
            continue
    return None
