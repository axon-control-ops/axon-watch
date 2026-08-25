"""Persisted worker delivery records (SQLite beside control-plane DB)."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from app.persistence.sqlite_connection import ManagedConnection

_LOCK = threading.Lock()
_MEMORY_CONN: sqlite3.Connection | None = None

WORKER_DELIVERY_STAGES = (
    "changed",
    "verified",
    "committed",
    "pushed",
    "pr_open",
    "ci_pending",
    "ci_green",
    "ci_red",
    "repairing",
    "escalated",
    "blocked",
    "no_change",
)


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _db_path() -> str | None:
    configured = os.environ.get("AXON_WATCH_CONTROL_PLANE_DB", "").strip()
    if not configured:
        return None
    path = Path(configured)
    return str(path.with_name(f"{path.stem}-workspace-delivery{path.suffix or '.sqlite3'}"))


def _connect() -> sqlite3.Connection:
    global _MEMORY_CONN
    path = _db_path()
    if path is None:
        if _MEMORY_CONN is None:
            _MEMORY_CONN = sqlite3.connect(
                ":memory:", check_same_thread=False, factory=ManagedConnection
            )
            _MEMORY_CONN.row_factory = sqlite3.Row
            _ensure_schema(_MEMORY_CONN)
        return _MEMORY_CONN
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_deliveries (
            delivery_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            task_id TEXT,
            stage TEXT NOT NULL,
            baseline_sha TEXT,
            worker_branch TEXT,
            commit_sha TEXT,
            draft_pr_url TEXT,
            ci_run_url TEXT,
            ci_conclusion TEXT,
            attempt INTEGER NOT NULL DEFAULT 0,
            attempt_budget INTEGER NOT NULL DEFAULT 3,
            blocker TEXT,
            isolation_root TEXT,
            refs_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_deliveries_run
        ON workspace_deliveries(run_id)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_workspace_deliveries_workspace_stage
        ON workspace_deliveries(workspace_id, stage, updated_at)
        """
    )
    connection.commit()


@contextmanager
def _managed() -> Iterator[sqlite3.Connection]:
    with _LOCK:
        conn = _connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            if _db_path() is not None:
                conn.close()


def reset_store_for_tests() -> None:
    global _MEMORY_CONN
    with _LOCK:
        if _MEMORY_CONN is not None:
            _MEMORY_CONN.close()
            _MEMORY_CONN = None
        path = _db_path()
        if path and Path(path).is_file():
            Path(path).unlink(missing_ok=True)


def _row_to_record(row: sqlite3.Row) -> dict[str, Any]:
    data = dict(row)
    try:
        refs = json.loads(str(data.get("refs_json") or "{}"))
    except json.JSONDecodeError:
        refs = {}
    if not isinstance(refs, dict):
        refs = {}
    data["refs"] = refs
    return data


def create_delivery(
    *,
    workspace_id: str,
    run_id: str,
    task_id: str | None = None,
    stage: str = "changed",
    baseline_sha: str | None = None,
    worker_branch: str | None = None,
    isolation_root: str | None = None,
    attempt_budget: int = 3,
    refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    delivery_id = f"wd_{uuid4().hex[:16]}"
    now = _utc_now_iso()
    payload_refs = dict(refs or {})
    with _managed() as conn:
        conn.execute(
            """
            INSERT INTO workspace_deliveries (
                delivery_id, workspace_id, run_id, task_id, stage,
                baseline_sha, worker_branch, commit_sha, draft_pr_url,
                ci_run_url, ci_conclusion, attempt, attempt_budget, blocker,
                isolation_root, refs_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, NULL, 0, ?, NULL, ?, ?, ?, ?)
            """,
            (
                delivery_id,
                workspace_id.strip(),
                run_id.strip(),
                (task_id or "").strip() or None,
                stage if stage in WORKER_DELIVERY_STAGES else "changed",
                (baseline_sha or "").strip() or None,
                (worker_branch or "").strip() or None,
                max(1, int(attempt_budget)),
                (isolation_root or "").strip() or None,
                json.dumps(payload_refs, sort_keys=True),
                now,
                now,
            ),
        )
    record = get_delivery(delivery_id)
    assert record is not None
    return record


def get_delivery(delivery_id: str) -> dict[str, Any] | None:
    with _managed() as conn:
        row = conn.execute(
            "SELECT * FROM workspace_deliveries WHERE delivery_id = ?",
            (delivery_id.strip(),),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def get_delivery_by_run(run_id: str) -> dict[str, Any] | None:
    with _managed() as conn:
        row = conn.execute(
            """
            SELECT * FROM workspace_deliveries
            WHERE run_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (run_id.strip(),),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def latest_workspace_delivery(workspace_id: str) -> dict[str, Any] | None:
    with _managed() as conn:
        row = conn.execute(
            """
            SELECT * FROM workspace_deliveries
            WHERE workspace_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (workspace_id.strip(),),
        ).fetchone()
    return _row_to_record(row) if row is not None else None


def update_delivery(
    delivery_id: str,
    *,
    stage: str | None = None,
    commit_sha: str | None = None,
    draft_pr_url: str | None = None,
    ci_run_url: str | None = None,
    ci_conclusion: str | None = None,
    attempt: int | None = None,
    blocker: str | None = None,
    isolation_root: str | None = None,
    refs: dict[str, Any] | None = None,
    clear_blocker: bool = False,
) -> dict[str, Any] | None:
    current = get_delivery(delivery_id)
    if current is None:
        return None
    next_stage = stage if stage in WORKER_DELIVERY_STAGES else current["stage"]
    next_refs = dict(current.get("refs") or {})
    if refs:
        next_refs.update(refs)
    if commit_sha is not None:
        next_refs["commit_sha"] = commit_sha
    if draft_pr_url is not None:
        next_refs["draft_pr_url"] = draft_pr_url
    if ci_run_url is not None:
        next_refs["ci_run_url"] = ci_run_url
    if ci_conclusion is not None:
        next_refs["ci_conclusion"] = ci_conclusion
    if attempt is not None:
        next_refs["attempt"] = attempt
    if blocker is not None:
        next_refs["blocker"] = blocker
    elif clear_blocker:
        next_refs.pop("blocker", None)
    now = _utc_now_iso()
    with _managed() as conn:
        conn.execute(
            """
            UPDATE workspace_deliveries
            SET stage = ?,
                commit_sha = COALESCE(?, commit_sha),
                draft_pr_url = COALESCE(?, draft_pr_url),
                ci_run_url = COALESCE(?, ci_run_url),
                ci_conclusion = COALESCE(?, ci_conclusion),
                attempt = COALESCE(?, attempt),
                blocker = CASE
                    WHEN ? THEN NULL
                    WHEN ? IS NOT NULL THEN ?
                    ELSE blocker
                END,
                isolation_root = COALESCE(?, isolation_root),
                refs_json = ?,
                updated_at = ?
            WHERE delivery_id = ?
            """,
            (
                next_stage,
                commit_sha,
                draft_pr_url,
                ci_run_url,
                ci_conclusion,
                attempt,
                1 if clear_blocker else 0,
                blocker,
                blocker,
                isolation_root,
                json.dumps(next_refs, sort_keys=True),
                now,
                delivery_id.strip(),
            ),
        )
    return get_delivery(delivery_id)


def find_delivery_by_branch_sha(
    *,
    workspace_id: str,
    worker_branch: str,
    commit_sha: str | None = None,
) -> dict[str, Any] | None:
    branch = worker_branch.strip()
    sha = (commit_sha or "").strip()
    with _managed() as conn:
        if sha:
            row = conn.execute(
                """
                SELECT * FROM workspace_deliveries
                WHERE workspace_id = ? AND worker_branch = ? AND commit_sha = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (workspace_id.strip(), branch, sha),
            ).fetchone()
        else:
            row = conn.execute(
                """
                SELECT * FROM workspace_deliveries
                WHERE workspace_id = ? AND worker_branch = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (workspace_id.strip(), branch),
            ).fetchone()
    return _row_to_record(row) if row is not None else None
