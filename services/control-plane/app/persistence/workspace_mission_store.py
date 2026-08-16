"""Durable cross-workspace mission and node ledger."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from typing import Any

from app.persistence import run_store_sqlite
from app.persistence.schema_serialization import serialized_schema

MISSION_STATUSES = frozenset({
    "planned", "running", "blocked", "verifying", "ready_for_promotion",
    "completed", "cancelled",
})


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@contextmanager
def _connection():
    connection = run_store_sqlite.connect(os.environ.get("AXON_WATCH_CONTROL_PLANE_DB"))
    try:
        ensure_schema(connection)
        yield connection
    finally:
        connection.close()


@serialized_schema
def ensure_schema(connection: Any) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS workspace_missions (
            mission_id TEXT PRIMARY KEY,
            dedupe_key TEXT NOT NULL UNIQUE,
            goal TEXT NOT NULL,
            status TEXT NOT NULL,
            risk TEXT NOT NULL DEFAULT 'normal',
            source_workspace_id TEXT NOT NULL,
            source_task_id TEXT,
            source_run_id TEXT,
            impact_json TEXT NOT NULL DEFAULT '[]',
            integration_manifest_json TEXT NOT NULL DEFAULT '{}',
            promotions_json TEXT NOT NULL DEFAULT '[]',
            blocker TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS workspace_mission_nodes (
            node_id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            workspace_id TEXT NOT NULL,
            task_id TEXT,
            owner_role TEXT NOT NULL DEFAULT '',
            relation TEXT NOT NULL DEFAULT 'affected',
            status TEXT NOT NULL DEFAULT 'planned',
            dependency_task_ids_json TEXT NOT NULL DEFAULT '[]',
            delivery_id TEXT,
            commit_sha TEXT,
            draft_pr_url TEXT,
            delivery_stage TEXT,
            verification_json TEXT NOT NULL DEFAULT '{}',
            blocker TEXT NOT NULL DEFAULT '',
            promotion_order INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(mission_id, workspace_id),
            FOREIGN KEY(mission_id) REFERENCES workspace_missions(mission_id)
        );
        CREATE INDEX IF NOT EXISTS idx_workspace_missions_status
            ON workspace_missions(status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_workspace_mission_nodes_workspace
            ON workspace_mission_nodes(workspace_id, status, updated_at DESC);
        """
    )
    connection.commit()
    mission_columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(workspace_missions)").fetchall()
    }
    for name, ddl in (
        ("integration_manifest_json", "TEXT NOT NULL DEFAULT '{}'"),
        ("promotions_json", "TEXT NOT NULL DEFAULT '[]'"),
    ):
        if name not in mission_columns:
            connection.execute(f"ALTER TABLE workspace_missions ADD COLUMN {name} {ddl}")
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(workspace_mission_nodes)").fetchall()
    }
    if "delivery_stage" not in columns:
        connection.execute("ALTER TABLE workspace_mission_nodes ADD COLUMN delivery_stage TEXT")
        connection.commit()


def _json(raw: Any, fallback: Any) -> Any:
    try:
        parsed = json.loads(str(raw or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed


def _mission(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["impact"] = _json(data.pop("impact_json", "[]"), [])
    data["integration_manifest"] = _json(data.pop("integration_manifest_json", "{}"), {})
    data["promotions"] = _json(data.pop("promotions_json", "[]"), [])
    return data


def _node(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["dependency_task_ids"] = _json(data.pop("dependency_task_ids_json", "[]"), [])
    data["verification"] = _json(data.pop("verification_json", "{}"), {})
    return data


def create_mission(record: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_missions
                (mission_id, dedupe_key, goal, status, risk, source_workspace_id,
                 source_task_id, source_run_id, impact_json, blocker, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["mission_id"], record["dedupe_key"], record["goal"],
                record.get("status", "planned"), record.get("risk", "normal"),
                record["source_workspace_id"], record.get("source_task_id"),
                record.get("source_run_id"), json.dumps(record.get("impact") or []),
                record.get("blocker", ""), now, now,
            ),
        )
        connection.commit()
    return get_mission(str(record["mission_id"])) or {}


def create_node(record: dict[str, Any]) -> dict[str, Any]:
    now = _now()
    with _connection() as connection:
        connection.execute(
            """
            INSERT INTO workspace_mission_nodes
                (node_id, mission_id, workspace_id, task_id, owner_role, relation,
                 status, dependency_task_ids_json, verification_json, blocker,
                 promotion_order, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["node_id"], record["mission_id"], record["workspace_id"],
                record.get("task_id"), record.get("owner_role", ""),
                record.get("relation", "affected"), record.get("status", "planned"),
                json.dumps(record.get("dependency_task_ids") or []),
                json.dumps(record.get("verification") or {}), record.get("blocker", ""),
                int(record.get("promotion_order") or 0), now, now,
            ),
        )
        connection.commit()
    return get_node(str(record["node_id"])) or {}


def get_node(node_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM workspace_mission_nodes WHERE node_id = ?", (node_id,)
        ).fetchone()
    return _node(row) if row is not None else None


def get_mission(mission_id: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT * FROM workspace_missions WHERE mission_id = ?", (mission_id,)
        ).fetchone()
        nodes = connection.execute(
            "SELECT * FROM workspace_mission_nodes WHERE mission_id = ? "
            "ORDER BY promotion_order, workspace_id",
            (mission_id,),
        ).fetchall()
    if row is None:
        return None
    return {**_mission(row), "nodes": [_node(item) for item in nodes]}


def get_by_dedupe_key(dedupe_key: str) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            "SELECT mission_id FROM workspace_missions WHERE dedupe_key = ?", (dedupe_key,)
        ).fetchone()
    return get_mission(str(row["mission_id"])) if row is not None else None


def list_missions(*, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    sql = "SELECT mission_id FROM workspace_missions"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    sql += " ORDER BY updated_at DESC LIMIT ?"
    params.append(max(1, min(int(limit), 500)))
    with _connection() as connection:
        rows = connection.execute(sql, tuple(params)).fetchall()
    return [record for row in rows if (record := get_mission(str(row["mission_id"]))) is not None]


def update_mission(mission_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "status", "blocker", "impact", "source_task_id", "source_run_id",
        "integration_manifest", "promotions",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if not updates:
        return get_mission(mission_id)
    if "status" in updates and updates["status"] not in MISSION_STATUSES:
        raise ValueError(f"invalid mission status: {updates['status']}")
    if "impact" in updates:
        updates["impact_json"] = json.dumps(updates.pop("impact"))
    if "integration_manifest" in updates:
        updates["integration_manifest_json"] = json.dumps(updates.pop("integration_manifest"))
    if "promotions" in updates:
        updates["promotions_json"] = json.dumps(updates.pop("promotions"))
    updates["updated_at"] = _now()
    with _connection() as connection:
        connection.execute(
            f"UPDATE workspace_missions SET {', '.join(f'{key} = ?' for key in updates)} "
            "WHERE mission_id = ?",
            (*updates.values(), mission_id),
        )
        connection.commit()
    return get_mission(mission_id)


def update_node(node_id: str, **fields: Any) -> dict[str, Any] | None:
    allowed = {
        "status", "task_id", "delivery_id", "commit_sha", "draft_pr_url",
        "delivery_stage", "verification", "blocker", "dependency_task_ids",
    }
    updates = {key: value for key, value in fields.items() if key in allowed}
    if "verification" in updates:
        updates["verification_json"] = json.dumps(updates.pop("verification"))
    if "dependency_task_ids" in updates:
        updates["dependency_task_ids_json"] = json.dumps(updates.pop("dependency_task_ids"))
    updates["updated_at"] = _now()
    with _connection() as connection:
        connection.execute(
            f"UPDATE workspace_mission_nodes SET {', '.join(f'{key} = ?' for key in updates)} "
            "WHERE node_id = ?",
            (*updates.values(), node_id),
        )
        connection.commit()
    return get_node(node_id)


def reset_store() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM workspace_mission_nodes")
        connection.execute("DELETE FROM workspace_missions")
        connection.commit()


def attach_task_mission(task_id: str, mission_id: str) -> None:
    with _connection() as connection:
        connection.execute(
            "UPDATE workspace_tasks SET mission_id = ?, updated_at = ? WHERE task_id = ?",
            (mission_id.strip(), _now(), task_id.strip()),
        )
        connection.commit()


__all__ = [
    "MISSION_STATUSES", "attach_task_mission", "create_mission", "create_node", "get_by_dedupe_key",
    "get_mission", "get_node", "list_missions", "reset_store", "update_mission",
    "update_node",
]
