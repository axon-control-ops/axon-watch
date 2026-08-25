"""SQLite-backed AXON-X constitution registry spine.

This module adds first-class registries required by the AXON-X Engineering
Constitution without replacing existing execution stores. Evidence records are
lightweight indexes that point at source receipts/history rows; source evidence
remains owned by the original subsystem.
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from typing import Any
from uuid import uuid4

from app.persistence import run_store_sqlite

REGISTRY_TABLES = (
    "evidence_registry",
    "mission_registry",
    "decision_registry",
    "capability_registry",
    "adr_registry",
    "technical_debt_registry",
    "platform_health_registry",
)


def _configured_db_path() -> str | None:
    return os.environ.get("AXON_WATCH_CONTROL_PLANE_DB")


def _connection():
    return run_store_sqlite.connect(_configured_db_path())


@contextmanager
def _managed_connection():
    connection = _connection()
    try:
        ensure_schema(connection)
        yield connection
    finally:
        connection.close()


def _utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _json_list(value: list[str] | None) -> str:
    return json.dumps([str(item).strip() for item in value or [] if str(item).strip()])


def _json_dict(value: dict[str, Any] | None) -> str:
    return json.dumps(value or {}, sort_keys=True)


def _decode_json(raw: Any, fallback: Any) -> Any:
    try:
        parsed = json.loads(str(raw or ""))
    except (TypeError, json.JSONDecodeError):
        return fallback
    return parsed


def ensure_schema(connection: Any) -> None:
    """Create constitution registries idempotently."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS evidence_registry (
            evidence_id TEXT PRIMARY KEY,
            source_table TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_ref_json TEXT NOT NULL DEFAULT '{}',
            kind TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            workspace_id TEXT NOT NULL DEFAULT '',
            run_id TEXT,
            task_id TEXT,
            mission_id TEXT,
            decision_id TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_evidence_registry_source
            ON evidence_registry(source_table, source_id);
        CREATE INDEX IF NOT EXISTS idx_evidence_registry_mission
            ON evidence_registry(mission_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_evidence_registry_run
            ON evidence_registry(run_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_evidence_registry_task
            ON evidence_registry(task_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS mission_registry (
            mission_id TEXT PRIMARY KEY,
            workspace_id TEXT NOT NULL DEFAULT '',
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            risk TEXT NOT NULL DEFAULT 'normal',
            lead_plan_id TEXT,
            success_criteria_json TEXT NOT NULL DEFAULT '[]',
            checkpoint_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_mission_registry_workspace_status
            ON mission_registry(workspace_id, status, updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_mission_registry_lead_plan
            ON mission_registry(lead_plan_id);

        CREATE TABLE IF NOT EXISTS decision_registry (
            decision_id TEXT PRIMARY KEY,
            actor TEXT NOT NULL,
            capability_id TEXT NOT NULL DEFAULT '',
            decision TEXT NOT NULL,
            tier TEXT NOT NULL DEFAULT '',
            risk TEXT NOT NULL DEFAULT 'normal',
            explanation TEXT NOT NULL DEFAULT '',
            confidence REAL,
            confidence_note TEXT NOT NULL DEFAULT '',
            mission_id TEXT,
            task_id TEXT,
            run_id TEXT,
            source_table TEXT NOT NULL DEFAULT '',
            source_id TEXT NOT NULL DEFAULT '',
            evidence_ids_json TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL DEFAULT 'recorded',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            resolved_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_decision_registry_mission
            ON decision_registry(mission_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decision_registry_task
            ON decision_registry(task_id, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_decision_registry_run
            ON decision_registry(run_id, created_at DESC);

        CREATE TABLE IF NOT EXISTS capability_registry (
            capability_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',
            owner_role TEXT NOT NULL DEFAULT '',
            route_paths_json TEXT NOT NULL DEFAULT '[]',
            adr_ids_json TEXT NOT NULL DEFAULT '[]',
            success_criteria_json TEXT NOT NULL DEFAULT '[]',
            version TEXT NOT NULL DEFAULT '0.1.0',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_capability_registry_name
            ON capability_registry(name);

        CREATE TABLE IF NOT EXISTS adr_registry (
            adr_id TEXT PRIMARY KEY,
            number INTEGER NOT NULL,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'proposed',
            doc_path TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            capability_ids_json TEXT NOT NULL DEFAULT '[]',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_adr_registry_number
            ON adr_registry(number);

        CREATE TABLE IF NOT EXISTS technical_debt_registry (
            debt_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            severity TEXT NOT NULL DEFAULT 'low',
            area TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open',
            evidence_ids_json TEXT NOT NULL DEFAULT '[]',
            adr_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_technical_debt_registry_status
            ON technical_debt_registry(status, severity, updated_at DESC);

        CREATE TABLE IF NOT EXISTS platform_health_registry (
            snapshot_id TEXT PRIMARY KEY,
            scope TEXT NOT NULL DEFAULT 'platform',
            status TEXT NOT NULL DEFAULT 'unknown',
            signals_json TEXT NOT NULL DEFAULT '{}',
            source TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_platform_health_registry_scope
            ON platform_health_registry(scope, created_at DESC);
        """
    )
    connection.commit()


def reset_store() -> None:
    with _managed_connection() as connection:
        for table in REGISTRY_TABLES:
            connection.execute(f"DELETE FROM {table}")
        connection.commit()


def _row_to_record(row: Any) -> dict[str, Any]:
    record = dict(row)
    for key in (
        "tags_json",
        "success_criteria_json",
        "checkpoint_json",
        "evidence_ids_json",
        "route_paths_json",
        "adr_ids_json",
        "capability_ids_json",
        "signals_json",
        "source_ref_json",
    ):
        if key in record:
            fallback: Any = {} if key.endswith("_ref_json") or key in {"checkpoint_json", "signals_json"} else []
            record[key.removesuffix("_json")] = _decode_json(record[key], fallback)
    return record


def registry_counts() -> dict[str, int]:
    with _managed_connection() as connection:
        return {
            table: int(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in REGISTRY_TABLES
        }


def index_evidence(
    *,
    source_table: str,
    source_id: str,
    source_ref: dict[str, Any] | None = None,
    kind: str = "",
    summary: str = "",
    workspace_id: str = "",
    run_id: str | None = None,
    task_id: str | None = None,
    mission_id: str | None = None,
    decision_id: str | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    cleaned_table = str(source_table or "").strip()
    cleaned_id = str(source_id or "").strip()
    if not cleaned_table or not cleaned_id:
        raise ValueError("source_table and source_id are required")
    now = _utc_now_iso()
    with _managed_connection() as connection:
        existing = connection.execute(
            "SELECT evidence_id FROM evidence_registry WHERE source_table = ? AND source_id = ?",
            (cleaned_table, cleaned_id),
        ).fetchone()
        evidence_id = str(existing["evidence_id"]) if existing else f"evidence-{uuid4().hex[:16]}"
        if existing:
            connection.execute(
                """
                UPDATE evidence_registry
                   SET source_ref_json = ?, kind = ?, summary = ?, workspace_id = ?,
                       run_id = ?, task_id = ?, mission_id = ?, decision_id = ?,
                       tags_json = ?, updated_at = ?
                 WHERE evidence_id = ?
                """,
                (
                    _json_dict(source_ref),
                    str(kind or ""),
                    str(summary or ""),
                    str(workspace_id or ""),
                    run_id,
                    task_id,
                    mission_id,
                    decision_id,
                    _json_list(tags),
                    now,
                    evidence_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO evidence_registry (
                    evidence_id, source_table, source_id, source_ref_json, kind,
                    summary, workspace_id, run_id, task_id, mission_id,
                    decision_id, tags_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    cleaned_table,
                    cleaned_id,
                    _json_dict(source_ref),
                    str(kind or ""),
                    str(summary or ""),
                    str(workspace_id or ""),
                    run_id,
                    task_id,
                    mission_id,
                    decision_id,
                    _json_list(tags),
                    now,
                    now,
                ),
            )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM evidence_registry WHERE evidence_id = ?",
            (evidence_id,),
        ).fetchone()
    return _row_to_record(row)


def list_evidence(
    *,
    mission_id: str | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    source_table: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (
        ("mission_id", mission_id),
        ("run_id", run_id),
        ("task_id", task_id),
        ("source_table", source_table),
    ):
        cleaned = str(value or "").strip()
        if cleaned:
            clauses.append(f"{column} = ?")
            params.append(cleaned)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _managed_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM evidence_registry {where} ORDER BY created_at DESC LIMIT ?",
            (*params, capped),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def create_mission(
    *,
    title: str,
    workspace_id: str = "",
    description: str = "",
    risk: str = "normal",
    lead_plan_id: str | None = None,
    success_criteria: list[str] | None = None,
) -> dict[str, Any]:
    cleaned_title = str(title or "").strip()
    if not cleaned_title:
        raise ValueError("title is required")
    now = _utc_now_iso()
    mission_id = f"mission-{uuid4().hex[:16]}"
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO mission_registry (
                mission_id, workspace_id, title, description, status, risk,
                lead_plan_id, success_criteria_json, checkpoint_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'active', ?, ?, ?, '{}', ?, ?)
            """,
            (
                mission_id,
                str(workspace_id or ""),
                cleaned_title,
                str(description or ""),
                str(risk or "normal").strip().lower() or "normal",
                lead_plan_id,
                _json_list(success_criteria),
                now,
                now,
            ),
        )
        connection.commit()
    mission = get_mission(mission_id)
    assert mission is not None
    return mission


def get_mission(mission_id: str) -> dict[str, Any] | None:
    cleaned = str(mission_id or "").strip()
    if not cleaned:
        return None
    with _managed_connection() as connection:
        row = connection.execute(
            "SELECT * FROM mission_registry WHERE mission_id = ?",
            (cleaned,),
        ).fetchone()
    return _row_to_record(row) if row else None


def mission_for_lead_plan(lead_plan_id: str) -> dict[str, Any] | None:
    cleaned = str(lead_plan_id or "").strip()
    if not cleaned:
        return None
    with _managed_connection() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM mission_registry
            WHERE lead_plan_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (cleaned,),
        ).fetchone()
    return _row_to_record(row) if row else None


def list_missions(*, workspace_id: str | None = None, status: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (("workspace_id", workspace_id), ("status", status)):
        cleaned = str(value or "").strip()
        if cleaned:
            clauses.append(f"{column} = ?")
            params.append(cleaned)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _managed_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM mission_registry {where} ORDER BY updated_at DESC LIMIT ?",
            (*params, capped),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def update_mission_checkpoint(mission_id: str, checkpoint: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            UPDATE mission_registry
               SET checkpoint_json = ?, updated_at = ?
             WHERE mission_id = ?
            """,
            (_json_dict(checkpoint), now, str(mission_id or "").strip()),
        )
        connection.commit()
    mission = get_mission(mission_id)
    if mission is None:
        raise ValueError(f"mission not found: {mission_id}")
    return mission


def record_decision(
    *,
    actor: str,
    decision: str,
    tier: str = "",
    risk: str = "normal",
    explanation: str = "",
    capability_id: str = "",
    confidence: float | None = None,
    confidence_note: str = "",
    mission_id: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    source_table: str = "",
    source_id: str = "",
    evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    cleaned_actor = str(actor or "").strip()
    cleaned_decision = str(decision or "").strip()
    if not cleaned_actor or not cleaned_decision:
        raise ValueError("actor and decision are required")
    if not evidence_ids and str(tier or "").strip().lower() in {"auto_safe", "operator_gated"}:
        raise ValueError("evidence_ids are required for autonomous/operator-gated decisions")
    now = _utc_now_iso()
    decision_id = f"decision-{uuid4().hex[:16]}"
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO decision_registry (
                decision_id, actor, capability_id, decision, tier, risk, explanation,
                confidence, confidence_note, mission_id, task_id, run_id,
                source_table, source_id, evidence_ids_json, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'recorded', ?, ?)
            """,
            (
                decision_id,
                cleaned_actor,
                str(capability_id or ""),
                cleaned_decision,
                str(tier or ""),
                str(risk or "normal"),
                str(explanation or ""),
                confidence,
                str(confidence_note or ""),
                mission_id,
                task_id,
                run_id,
                str(source_table or ""),
                str(source_id or ""),
                _json_list(evidence_ids),
                now,
                now,
            ),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM decision_registry WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
    return _row_to_record(row)


def list_decisions(
    *,
    mission_id: str | None = None,
    task_id: str | None = None,
    run_id: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in (("mission_id", mission_id), ("task_id", task_id), ("run_id", run_id)):
        cleaned = str(value or "").strip()
        if cleaned:
            clauses.append(f"{column} = ?")
            params.append(cleaned)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _managed_connection() as connection:
        rows = connection.execute(
            f"SELECT * FROM decision_registry {where} ORDER BY created_at DESC LIMIT ?",
            (*params, capped),
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def upsert_capability(
    *,
    name: str,
    capability_id: str | None = None,
    description: str = "",
    status: str = "active",
    owner_role: str = "",
    route_paths: list[str] | None = None,
    adr_ids: list[str] | None = None,
    success_criteria: list[str] | None = None,
    version: str = "0.1.0",
) -> dict[str, Any]:
    cleaned_name = str(name or "").strip()
    if not cleaned_name:
        raise ValueError("name is required")
    now = _utc_now_iso()
    with _managed_connection() as connection:
        existing = connection.execute(
            "SELECT capability_id FROM capability_registry WHERE name = ?",
            (cleaned_name,),
        ).fetchone()
        cleaned_capability_id = str(capability_id or "").strip()
        if cleaned_capability_id and not cleaned_capability_id.startswith("CAP-"):
            raise ValueError("capability_id must use the CAP-### form")
        stored_capability_id = (
            str(existing["capability_id"])
            if existing
            else cleaned_capability_id or f"cap-{uuid4().hex[:16]}"
        )
        if existing:
            connection.execute(
                """
                UPDATE capability_registry
                   SET description = ?, status = ?, owner_role = ?,
                       route_paths_json = ?, adr_ids_json = ?,
                       success_criteria_json = ?, version = ?, updated_at = ?
                 WHERE capability_id = ?
                """,
                (
                    str(description or ""),
                    str(status or "active"),
                    str(owner_role or ""),
                    _json_list(route_paths),
                    _json_list(adr_ids),
                    _json_list(success_criteria),
                    str(version or "0.1.0"),
                    now,
                    stored_capability_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO capability_registry (
                    capability_id, name, description, status, owner_role,
                    route_paths_json, adr_ids_json, success_criteria_json,
                    version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    stored_capability_id,
                    cleaned_name,
                    str(description or ""),
                    str(status or "active"),
                    str(owner_role or ""),
                    _json_list(route_paths),
                    _json_list(adr_ids),
                    _json_list(success_criteria),
                    str(version or "0.1.0"),
                    now,
                    now,
                ),
            )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM capability_registry WHERE capability_id = ?",
            (stored_capability_id,),
        ).fetchone()
    return _row_to_record(row)


def list_capabilities(*, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 200), 500))
    with _managed_connection() as connection:
        if status:
            rows = connection.execute(
                "SELECT * FROM capability_registry WHERE status = ? ORDER BY name LIMIT ?",
                (status, capped),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM capability_registry ORDER BY name LIMIT ?",
                (capped,),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def upsert_adr(
    *,
    number: int,
    title: str,
    status: str = "proposed",
    doc_path: str = "",
    summary: str = "",
    capability_ids: list[str] | None = None,
) -> dict[str, Any]:
    cleaned_title = str(title or "").strip()
    if not cleaned_title:
        raise ValueError("title is required")
    now = _utc_now_iso()
    with _managed_connection() as connection:
        existing = connection.execute(
            "SELECT adr_id FROM adr_registry WHERE number = ?",
            (int(number),),
        ).fetchone()
        adr_id = str(existing["adr_id"]) if existing else f"adr-{uuid4().hex[:16]}"
        if existing:
            connection.execute(
                """
                UPDATE adr_registry
                   SET title = ?, status = ?, doc_path = ?, summary = ?,
                       capability_ids_json = ?, updated_at = ?
                 WHERE adr_id = ?
                """,
                (
                    cleaned_title,
                    str(status or "proposed"),
                    str(doc_path or ""),
                    str(summary or ""),
                    _json_list(capability_ids),
                    now,
                    adr_id,
                ),
            )
        else:
            connection.execute(
                """
                INSERT INTO adr_registry (
                    adr_id, number, title, status, doc_path, summary,
                    capability_ids_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    adr_id,
                    int(number),
                    cleaned_title,
                    str(status or "proposed"),
                    str(doc_path or ""),
                    str(summary or ""),
                    _json_list(capability_ids),
                    now,
                    now,
                ),
            )
        connection.commit()
        row = connection.execute("SELECT * FROM adr_registry WHERE adr_id = ?", (adr_id,)).fetchone()
    return _row_to_record(row)


def list_adrs(*, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 200), 500))
    with _managed_connection() as connection:
        if status:
            rows = connection.execute(
                "SELECT * FROM adr_registry WHERE status = ? ORDER BY number LIMIT ?",
                (status, capped),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM adr_registry ORDER BY number LIMIT ?",
                (capped,),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def record_debt(
    *,
    title: str,
    description: str = "",
    severity: str = "low",
    area: str = "",
    evidence_ids: list[str] | None = None,
    adr_id: str | None = None,
) -> dict[str, Any]:
    cleaned_title = str(title or "").strip()
    if not cleaned_title:
        raise ValueError("title is required")
    now = _utc_now_iso()
    debt_id = f"debt-{uuid4().hex[:16]}"
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO technical_debt_registry (
                debt_id, title, description, severity, area, status,
                evidence_ids_json, adr_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'open', ?, ?, ?, ?)
            """,
            (
                debt_id,
                cleaned_title,
                str(description or ""),
                str(severity or "low"),
                str(area or ""),
                _json_list(evidence_ids),
                adr_id,
                now,
                now,
            ),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM technical_debt_registry WHERE debt_id = ?",
            (debt_id,),
        ).fetchone()
    return _row_to_record(row)


def list_debt(*, status: str | None = "open", limit: int = 100) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 100), 500))
    with _managed_connection() as connection:
        if status:
            rows = connection.execute(
                """
                SELECT * FROM technical_debt_registry
                WHERE status = ?
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (status, capped),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM technical_debt_registry ORDER BY updated_at DESC LIMIT ?",
                (capped,),
            ).fetchall()
    return [_row_to_record(row) for row in rows]


def record_health_snapshot(
    *,
    scope: str = "platform",
    status: str,
    signals: dict[str, Any] | None = None,
    source: str = "",
) -> dict[str, Any]:
    cleaned_status = str(status or "").strip()
    if not cleaned_status:
        raise ValueError("status is required")
    snapshot_id = f"health-{uuid4().hex[:16]}"
    now = _utc_now_iso()
    with _managed_connection() as connection:
        connection.execute(
            """
            INSERT INTO platform_health_registry (
                snapshot_id, scope, status, signals_json, source, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot_id,
                str(scope or "platform"),
                cleaned_status,
                _json_dict(signals),
                str(source or ""),
                now,
            ),
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM platform_health_registry WHERE snapshot_id = ?",
            (snapshot_id,),
        ).fetchone()
    return _row_to_record(row)


def list_health_snapshots(*, scope: str = "platform", limit: int = 50) -> list[dict[str, Any]]:
    capped = max(1, min(int(limit or 50), 200))
    with _managed_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM platform_health_registry
            WHERE scope = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (str(scope or "platform"), capped),
        ).fetchall()
    return [_row_to_record(row) for row in rows]
